import sys
import splunk.entity as en
from splunklib.searchcommands import \
    dispatch, StreamingCommand, Configuration

from CMXUtil import *
import splunk.Intersplunk
import operator
import json


logger = get_logger("CMX_FLOOR")
@Configuration()
class cmxfloorinfoCommand(StreamingCommand):
    """
        This Command will traverse through the cmxmap source type to fetch details about Campus Name, Building Name and
        Floor Name along with various image parameters.

        ##Syntax

        .. code-block::
        cmxfloorinfo

        ##Description

        Returns floor information from the cmxmap.

        ##Example


        code-block::
            `cmx_index` sourcetype=cmxmap | table _raw | cmxfloorinfo

    """

    def stream(self, events):
        logger.info("Stream called ")

        data={}
        for event in events:
            logger.info(event.keys())
            campuses = json.loads(event["_raw"])
            for campus in campuses["campuses"]:
                campus_name = campus["name"]
                data["CampusName"] = campus_name
                for building in campus["buildingList"]:
                    data["BuildingName"] = building["name"]
                    for floor in building["floorList"]:
                        logger.info(floor["image"].keys())
                        data["FloorName"] = floor["name"]
                        logger.info(floor["image"]["height"])
                        data["image_height"] = floor["image"]["height"]
                        data["image_width"] = floor["image"]["width"]
                        data["image_size"] = floor["image"]["size"]
                        data["image_zoom_level"] = floor["image"]["zoomLevel"]
                        data["image_max_resolution"] = floor["image"]["maxResolution"]
                        data["FloorID"] = floor["aesUid"]
                        logger.info("HERE")
                        data["image_name"] = str(floor["aesUid"]) + ".png"
                        logger.info("HERE AAA")
                        yield data




dispatch(cmxfloorinfoCommand, sys.argv, sys.stdin, sys.stdout, __name__)
