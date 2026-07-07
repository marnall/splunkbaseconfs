# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

try:
    import http.client as httplib
except ImportError:
    import httplib
import sys

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
import itsi_path  # noqa

# Process .pth files
import site

from itsi.content_packs.constants import ContentPackInstallOptions
from itsi.content_packs.journal import TransactionJournal
from itsi.itsi_utils import ITOAInterfaceUtils
from itsi.rest_handler import rest_interface_splunkd
from itsi.rest_handler.rest_interface_splunkd import route


class ContentPacksInterface(rest_interface_splunkd.BaseRestInterfaceSplunkd):
    """Handles ITSI Content Pack REST operations."""

    @route('/{content_pack_id}/{version}/install', methods=['POST'])
    def install(self, request, content_pack_id, version):
        """
        Installs a content pack based on the given content pack id and version.

        :param request: the request
        :type request: Request

        :param content_pack_id: the content pack id
        :type content_pack_id: str

        :param version: the content pack version
        :type version: str

        :return: a tuple of response status code, and data
        :rtype: tuple of (int, object)
        """
        from itsi.content_packs.installer import install, LOGGER, update_saved_searches_status
        from itsi.content_packs.retriever import retrieve_one

        try:
            session_key = request.session['authtoken']
            action = request.data.get(ContentPackInstallOptions.SAVED_SEARCH_ACTION,
                                      ContentPackInstallOptions.SAVED_SEARCH_RETAIN_STATUS).lower()
            install_all = request.data.get(ContentPackInstallOptions.INSTALL_ALL, False)
            content_pack_name = ''
            transaction_id = ''
            if len(request.data.get(ContentPackInstallOptions.CONTENT)) > 0 or install_all:
                try:
                    content_pack_name = retrieve_one(content_pack_id, version, session_key)['title']
                except Exception as ex:
                    LOGGER.info(f'Failed to retrieve content pack name due to {ex}')
                journal, transaction_id = install(
                    content_pack_id,
                    version,
                    session_key=session_key,
                    options=request.data
                )
                search_page_url = f'app/itsi/search?q=search%20index%3D_internal%20tid%3D{transaction_id}%20source%3D*itsi_content_packs_install.log*' \
                    '&display.page.search.mode=smart&dispatch.sample_ratio=1&workload_pool=&earliest=-24h%40h&latest=now'
                installation_complete_message = f'Installation of {content_pack_name} is complete. [[{search_page_url}|View logs.]]'
                ITOAInterfaceUtils.create_message(
                    session_key,
                    installation_complete_message,
                    name=f'{transaction_id}-installed',
                    role='itoa_admin'
                )
            else:
                journal = TransactionJournal()
                journal.success([])
                journal.failure([])
            saved_searches = update_saved_searches_status(
                content_pack_id=content_pack_id,
                session_key=session_key,
                action=action
            )
            journal['saved_searches'] = saved_searches

        except Exception as ex:
            LOGGER.error('Failed install of content_pack_id="%s" version="%s"', content_pack_id, version)
            LOGGER.exception(ex)
            search_page_error_url = 'app/itsi/search?q=search%20index%3D_internal%20source%3D*itsi_content_packs_install.log*%20ERROR' \
                '&display.page.search.mode=smart&dispatch.sample_ratio=1&workload_pool=&earliest=-24h%40h&latest=now'
            if content_pack_name:
                installation_failed_message = f'Installation of {content_pack_name} failed. [[{search_page_error_url}|View logs.]]'
            else:
                installation_failed_message = f'Installation of content pack with id {content_pack_id} failed. [[{search_page_error_url}|View logs.]]'
                content_pack_name = content_pack_id

            ITOAInterfaceUtils.create_message(
                session_key,
                installation_failed_message,
                name=f'{content_pack_name}-failed-install',
                role='itoa_admin'
            )
            return httplib.INTERNAL_SERVER_ERROR, str(ex)

        LOGGER.info(f'tid={transaction_id} {journal}')
        return httplib.OK, journal

    @route('', methods=['GET'])
    def retrieve_all(self, request):
        """
        Returns all content packs for the given request parameters.

        :param request: the request
        :type request: Request

        :return: the content packs data
        :rtype: dict
        """
        from itsi.content_packs.retriever import retrieve_all, LOGGER

        try:
            items = retrieve_all(
                getargs=request.query,
                session_key=request.session['authtoken']
            )
        except Exception as ex:
            LOGGER.exception(ex)

            return httplib.INTERNAL_SERVER_ERROR, str(ex)

        return httplib.OK, {
            'items': items
        }

    @route('/{content_pack_id}/{version}', methods=['GET'])
    def retrieve_one(self, request, content_pack_id, version):
        """
        Returns the content data for the given content pack id and version.

        :param request: the request
        :type request: Request

        :param content_pack_id: the content pack id
        :type content_pack_id: str

        :param version: the content pack version
        :type version: str

        :return: the content packs data
        :rtype: dict
        """
        from itsi.content_packs.retriever import retrieve_one, LOGGER

        try:
            item = retrieve_one(
                content_pack_id=content_pack_id,
                version=version,
                session_key=request.session['authtoken']
            )
        except Exception as ex:
            LOGGER.exception(ex)

            return httplib.INTERNAL_SERVER_ERROR, str(ex)

        return httplib.OK, item

    @route('/{content_pack_id}/{version}/preview', methods=['GET'])
    def preview(self, request, content_pack_id, version):
        """
        Preview content pack objects based on the given content pack id and version.

        :param request: the request
        :type request: Request

        :param content_pack_id: the content pack id
        :type content_pack_id: str

        :param version: the content pack version
        :type version: str

        :return: a tuple of response status code, and data
        :rtype: tuple of (int, object)
        """
        from itsi.content_packs.preview import preview, LOGGER

        try:
            item = preview(
                content_pack_id=content_pack_id,
                version=version,
                session_key=request.session['authtoken']
            )
        except Exception as ex:
            LOGGER.exception(ex)

            return httplib.INTERNAL_SERVER_ERROR, str(ex)

        return httplib.OK, item

    @route('/status', methods=['GET'])
    def status(self, request):
        """
        Returns all content packs status for the given request parameters, used for telemtry.

        :param request: the request
        :type request: Request

        :return: the content packs data
        :rtype: dict
        """
        from itsi.content_packs.retriever import LOGGER
        from itsi.objects.itsi_content_pack_status import ItsiContentPackStatus
        import json

        try:
            installed_content_pack = ItsiContentPackStatus(
                request.session['authtoken'], 'nobody'
            ).get_bulk('nobody', fields=['installed_versions', '_key'])
            items = json.dumps(installed_content_pack)
        except Exception as ex:
            LOGGER.exception(ex)
            return httplib.INTERNAL_SERVER_ERROR, str(ex)

        return httplib.OK, items

    @route('/refresh', methods=['POST'])
    def refresh_content_library(self, request):
        """
        :param request: the request
        :type request: Request

        :return: apps added and removed from itsi_content_packs.conf
        :rtype: dict
        """
        from itsi.content_packs.content_library_refresh import refresh_using_configparser
        from itsi.content_packs.retriever import LOGGER
        from ITOA.setup_logging import setup_logging

        try:
            logger = setup_logging(
                logger_name='itsi_content_pack_authorship.refresh',
                logfile_name='itsi_content_pack_authorship.log'
            )
            payload = refresh_using_configparser(request.session['authtoken'], logger)
        except Exception as ex:
            LOGGER.exception(ex)
            return httplib.INTERNAL_SERVER_ERROR, str(ex)

        return httplib.OK, payload

    @route('/refresh_template', methods=['POST'])
    def refresh_template_conf(self, request):
        """
        :param request: the request
        :type request: Request

        :return: apps added and removed from itsi_content_packs.conf
        :rtype: dict
        """
        from itsi.content_packs.content_library_refresh import refresh_template_conf_to_kvstore
        from itsi.content_packs.installer import LOGGER
        from ITOA.setup_logging import setup_logging

        try:
            logger = setup_logging(
                logger_name='itsi_content_packs_itoa.refresh_template',
                logfile_name='itsi_content_packs_itoa.log'
            )
            payload = refresh_template_conf_to_kvstore(request.session['authtoken'], logger)
        except Exception as ex:
            LOGGER.exception(ex)
            return httplib.INTERNAL_SERVER_ERROR, str(ex)

        return httplib.OK, payload
