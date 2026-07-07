import os
import sys
bin_path = os.path.join(os.path.dirname(__file__))
if bin_path not in sys.path:
    sys.path.insert(0, bin_path)
lib_path = os.path.join(os.path.dirname(__file__), "..", "lib")
if lib_path not in sys.path:
    sys.path.insert(0, lib_path)
import splunk
from base_handler import BaseRestHandler
from urllib.parse import parse_qs
import re
import exceptions
import datetime

dockerfile_replace_from_key = "###FROM###"
dockerfile_replace_install_key = "###INSERT_pip_install###"
dockerfile = """
FROM ###FROM###
###INSERT_pip_install###
RUN chgrp -R 0 /dltk && \
    chmod -R g=u /dltk
RUN chgrp -R 0 /srv && \
    chmod -R g=u /srv
RUN chmod g+w /etc/passwd
USER 1001
EXPOSE 5000 8888 6000 6006
ENTRYPOINT ["/dltk/bootstrap_fast.sh"]
"""

class BuildHandler(BaseRestHandler):
    def handle_POST(self):
        try:
            self.get_logger().info("docker image build : %s", "Start")
            params = parse_qs(self.request['payload'])
            base_image = params["base_image"][0] if "base_image" in params else ''
            repo_name = params["repo_name"][0] if "repo_name" in params else ''
            image_name = params["image_name"][0] if "image_name" in params else ''
            installer = params["installer"][0] if "installer" in params else 'pip'
            image_title = params["image_title"][0] if "image_title" in params else ''
            requirements = params["requirements"][0] if "requirements" in params else ''
            image_push = params["image_push"][0] if "image_push" in params else ''

            results = {}
            results["ping_docker"] = "success"
            results["base_image"] = base_image
            results["repo_name"] = repo_name
            results["image_name"] = image_name
            results["installer"] = installer
            results["image_title"] = image_title
            results["requirements"] = requirements
            results["image_push"] = image_push

            if self.docker_client.ping() == False:
                self.send_json_response({"error": "Could not ping Docker"})
                results["ping_docker"] = "error"
                raise splunk.RESTException(400, "Could not ping Docker")
            
            # stanza name = key of repo + image name
            stanza_name = repo_name + image_name

            # validate requirements file
            # ^\w+(?:==[\d+\.]+)?$
            p=re.compile(r'^\w+(?:==[\d+\.]+)?$', re.M)
            reqs=p.findall(requirements)
            self.get_logger().info("docker image pip install requirements found : %s", str(len(reqs)))
            requirements = '\n'.join(reqs)
            self.get_logger().info("docker image pip install : %s", requirements)
            # force installer to pip only for now
            installer = "pip"

            # construct dockerfile
            final_requirements = "RUN " + installer + " install " + requirements.replace("\n"," ").replace("  "," ") if requirements else ""
            final_dockerfile = dockerfile.replace(dockerfile_replace_install_key, final_requirements).replace(dockerfile_replace_from_key, base_image)
            from io import BytesIO
            fileObj = BytesIO(bytes(final_dockerfile,'utf-8'))
            fileObj.seek(0)
            
            # start the build process and log events into splunk internal index
            self.get_logger().info("docker image start build process : %s", stanza_name)
            built_image, logs = self.docker_client.images.build(fileobj=fileObj, tag=stanza_name)
            for log in logs:
                self.get_logger().info("docker build process log repo_name=%s image_name=%s log_line=%s" % (repo_name, image_name, log))
            self.get_logger().info("docker image end build process : %s", stanza_name)
            build_time = datetime.datetime.now()

            self.get_logger().info("docker image push flag image_push : %s", image_push)
            if image_push=="docker_push":
                for line in self.docker_client.images.push(stanza_name, stream=True, decode=True):
                    self.get_logger().info("docker build process log image push repo_name=%s image_name=%s log_line=%s" % (repo_name, image_name, line))

            # update images.conf 
            if not stanza_name in self.image_stanzas:
                image_stanza = self.image_stanzas.create(stanza_name)
            else:
                image_stanza = self.image_stanzas[stanza_name]


            image_stanza.submit({
                "image": image_name,
                "base_image": base_image,
                "repo": repo_name,
                "installer": installer,
                "title": image_title,
                "runtime": "none,nvidia" if "gpu" in base_image else "none",
                "build_time": str(build_time),
                "image_id": built_image.id,
                "image_push": image_push,
                "requirements": requirements,
            })
            results["build_time"] = str(build_time)
            results["image_id"] = built_image.id
            self.send_json_response(results)

        except exceptions.ApplicationError:
            raise
        except:
            import traceback
            raise Exception(traceback.format_exc())

    def handle_GET(self):
        # TODO get all custom build image list similar to images endpoint, but only for the custom ones
        entries = []
        image_by_name = dict()
        for stanza in self.image_stanzas:
            image_by_name[stanza.name] = stanza
            # only list images with complete image names
            if "image" in stanza:
                e = {
                    "name": stanza.name,
                    "image": stanza.image,
                    "repo": stanza.repo,
                    "runtime": stanza.runtime,
                    "base_image": stanza.base_image if "base_image" in stanza else "",
                    "installer": stanza.installer if "installer" in stanza else "",
                    "title": stanza.title if "title" in stanza else "",
                    "build_time": stanza.build_time if "build_time" in stanza else "",
                    "image_id": stanza.image_id if "image_id" in stanza else "",
                    "image_push": stanza.image_push if "image_push" in stanza else "",
                    "requirements": stanza.requirements if "requirements" in stanza else "",
                }            
                entries.append(e)
        self.send_entries(entries)
        #self.send_json_response({})
