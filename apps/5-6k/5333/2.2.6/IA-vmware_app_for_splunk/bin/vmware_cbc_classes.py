

import vmware_paths
from cbc_sdk.platform import Observation, Device


class EnrichedEventObservationJson(Observation):
    def __init__(self, cb, model_unique_id=None, initial_data=None, force_init=False, full_doc=True):
        """
        Initialize the EnrichedEventObservationJson object.

        Args:
            cb (CBCloudAPI): A reference to the CBCloudAPI object.
            model_unique_id (Any): The unique ID for this particular instance of the model object.
            initial_data (dict): The data to use when initializing the model object.
            force_init (bool): True to force object initialization.
            full_doc (bool): True to mark the object as fully initialized.
        """
        self._details_timeout = 0
        self._info = None
        super(EnrichedEventObservationJson, self).__init__(cb, model_unique_id=model_unique_id,
                                                           initial_data=initial_data,
                                                           force_init=force_init, full_doc=full_doc)

    def json(self):
        return self._info


class EnrichedEventDeviceJson(Device):
    def __init__(self, cb, model_unique_id=None, initial_data=None, force_init=False, full_doc=True):
        """
        Initialize the EnrichedEventDeviceJson object.

        Args:
            cb (CBCloudAPI): A reference to the CBCloudAPI object.
            model_unique_id (Any): The unique ID for this particular instance of the model object.
            initial_data (dict): The data to use when initializing the model object.
            force_init (bool): True to force object initialization.
            full_doc (bool): True to mark the object as fully initialized.
        """
        self._details_timeout = 0
        self._info = None
        super(EnrichedEventDeviceJson, self).__init__(cb, model_unique_id=model_unique_id,
                                                           initial_data=initial_data,
                                                           force_init=force_init, full_doc=full_doc)

    def json(self):
        return self._info
