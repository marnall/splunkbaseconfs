# Copyright (C) 2005-2026 Splunk Inc. All Rights Reserved.

from abc import ABCMeta, abstractmethod
import json
import os.path as path

from rest_handler.session import session
from logging_utils.log import getLogger

import ite_constants
from ite_models.ite_model_procedure import IteProcedure
from ite_models.ite_model_use_case import IteUseCase
from ite_models.ite_model_use_case_family import IteUseCaseFamily
from ite_models.ite_model_maturity_stage import IteMaturityStage
from ite_models.ite_base_persistent_object import IteBasePersistentObject

logger = getLogger()


class DataLoader(object):
    """
    DataLoader loads data from a source into a destination. The behavior of a data loader can be extended
    by subclassing and overwrite the lifecycle methods like `before_run`, `post_run` and `transform`.
    """
    def __init__(self, source, destination):
        self.source = source
        self.destination = destination
        self.source_data = None
        session.save(req_source=ite_constants.REQ_SOURCE_DATA_LOADER)
        if not (isinstance(self.source, Storage) and isinstance(self.destination, Storage)):
            raise ValueError(
                'Both source and destination must be of type %s - got %s and %s instead' % (
                    Storage.__name__,
                    type(self.source),
                    type(self.destination)
                )
            )

    def before_run(self):
        """
        before_run will be executed before the main `run` method, it could be used as a
        preparation step to load additional data that will be referenced in the data loading
        process.

        To be overwritten by subclass.
        """
        pass

    def run(self):
        """
        run is the main method that will read from source, apply transformation and write to destination.
        Its behavior can be extended by implementing the other lifecycle and transformation methods.
        """
        try:
            self.before_run()
            self.source_data = self.source.read()
            transformed_data = self.transform()
            self.destination.write(transformed_data)
            self.post_run()
        except Exception:
            logger.exception('Failed to run data loader')

    def transform(self):
        """
        transform can be used to transform the data read from source before it's written to the destination.

        To be overwritten by subclass.

        :return: list of objects to write to destination
        :rtype: list
        """
        pass

    def post_run(self):
        """
        post_run will be executed after the main `run` method, it could be used as a cleanup step
        to delete any leftover artifact or objects created during/outside of the data loading process.

        To be overwritten by subclass.
        """
        pass


class Storage(metaclass=ABCMeta):
    """
    Storage is a abstract base class that represents a `Storage` that can be `read` from and `write` to.

    It should be subclassed to implement specific kind of storage.
    """

    def read(self, **kwargs):
        """
        Read from storage

        :return: Data read from storage
        """
        raise NotImplementedError()

    def write(self, data, **kwargs):
        """
        Write to storage

        :param data: Data to write to storage
        """
        raise NotImplementedError()


class Source(Storage):
    """
    Source represents a `Storage` that MUST be able to `read` from.

    It should be subclassed to implement specific kind of storage source.
    """
    @abstractmethod
    def read(self, **kwargs):
        pass


class Destination(Storage):
    """
    Destination represents a `Storage` that MUST be able to `write` to.

    It should be subclassed to implement specific kind of storage destination.
    """
    @abstractmethod
    def write(self, data, **kwargs):
        pass


class IteObjectInitializer(DataLoader):
    """
    IteObjectInitializer is a data loader implementation that loads a kind of ITE object from a source file
    into its corresponding KVStore collection. This initializer treats the source file as the source of truth
    and will insert any new objects, delete any old objects (not present in the source file anymore), and update
    any existing object with new content (The update/deletion behavior for existing objects can be customized
    by overwritting the `should_overwrite_with_source` and `merge_existing_with_source_obj` methods)
    """
    def __init__(self, source_file_path, ite_object_cls, should_keep_old=False):
        """
        :param source_file_path: (str) Source file that contains all the ITE objects data
        :param ite_object_cls: (IteBasePersistentObject) Class for the ITE object to load
        :param should_keep_old: (bool) (Optional) Should old contents not exist in source anymore be kept
        """
        super(IteObjectInitializer, self).__init__(
            source=FlatFileSource(source_file_path),
            destination=IteObjectKVStoreDestination(ite_object_cls)
        )
        self.source_file_path = source_file_path
        self.ite_object_cls = ite_object_cls
        self.should_keep_old = should_keep_old

    def before_run(self):
        self._get_existing_ite_objects_map()
        logger.info('Loaded all existing %s - count: %d', self.ite_object_cls.__name__, len(self.existing_objects_map))

    def transform(self):
        objects_to_upsert = self._get_entities_from_source_to_upsert()
        return objects_to_upsert

    def post_run(self):
        if not self.should_keep_old:
            self._delete_objects_no_longer_exists_in_source()

    def _get_existing_ite_objects_map(self):
        if getattr(self, 'existing_objects_map', None) is not None:
            return self.existing_objects_map
        existing_objects = self.ite_object_cls.load()
        self.existing_objects_map = {obj.key: obj for obj in existing_objects}
        return self.existing_objects_map

    def _get_entities_from_source_to_upsert(self):
        existing_objects_map = self._get_existing_ite_objects_map()
        objects_to_upsert = []
        if self.ite_object_cls == IteProcedure:
            source_use_case_ids = {p.get('use_case_id') for p in self.source_data}
        for obj in self.source_data:
            obj_key = obj.get('_key')
            if not obj_key:
                raise ValueError('ITE objects in source must contain a "key" field')

            existing_object = existing_objects_map.get(obj_key)
            if existing_object is None:
                objects_to_upsert.append(obj)
            else:
                merged_obj = self.merge_existing_with_source_obj(existing_object, obj)
                if self.should_overwrite_with_source(existing_object):
                    objects_to_upsert.append(merged_obj)
                else:
                    # This is to handle the case where existing procedure is marked as modified
                    # but it's use case doesn't exist anymore - in this case, we'll overwrite it
                    # with the new Procedure. Note that as of now, a Procedure is marked as modified
                    # when a user marks it as fav or deployed
                    if self.ite_object_cls == IteProcedure and existing_object.use_case_id not in source_use_case_ids:
                        objects_to_upsert.append(merged_obj)

        return objects_to_upsert

    def _delete_objects_no_longer_exists_in_source(self):
        existing_objects_map = self._get_existing_ite_objects_map()
        new_key_set = set([obj['_key'] for obj in self.source_data])
        keys_to_delete = []
        for key, obj in existing_objects_map.items():
            if self.should_overwrite_with_source(obj) and key not in new_key_set:
                keys_to_delete.append(key)
        if len(keys_to_delete):
            self.ite_object_cls.storage_bulk_delete(delete_query={'$or': [{'_key': key} for key in keys_to_delete]})
            logger.info(
                'Finished deleting non-existent %s - count: %d', self.ite_object_cls.__name__, len(keys_to_delete)
            )

    def should_overwrite_with_source(self, existing_obj):
        """
        should_overwrite_with_source determines if existing object should be overwritten with source.
        Defaults to True.

        :param existing_object: (IteBasePersistentObject) An existing object
        """
        return True

    def merge_existing_with_source_obj(self, existing_obj, source_obj):
        """
        merge_existing_with_source_obj merges an `existing_obj` with `source_obj` from the source file.
        Default behavior is to use data from source completely.

        :param existing_obj: (IteBasePersistentObject) An existing object
        :param source_obj: (dict) A dict representing data of obj from source
        :return: (dict) merged object
        """
        return source_obj

    def reset_destination_with_source(self, key):
        """
        reset_destination_with_source resets an object from the source file.

        :param key: key of the object to reset
        :return: key of the reset object, None if not found
        """
        if self.source_data is None:
            self.source_data = self.source.read()
        key_found = False
        for obj in self.source_data:
            obj_key = obj.get('_key')
            if obj_key == key:
                key_found = True
                break

        if not key_found:
            return None
        else:
            self.destination.write([obj])
        return obj


class FlatFileSource(Source):
    """
    FlatFileSource represents a source of data that should be read from a file on disk.
    """
    def __init__(self, filepath, file_format='json'):
        super(FlatFileSource, self).__init__()
        self.filepath = filepath
        self.format = file_format

    def read(self, **kwargs):
        with open(self.filepath, 'rb') as f:
            if self.format == 'json':
                logger.info('reading content from json file at %s...', self.filepath)
                content = f.read()
                json_data = json.loads(content)
                json_data = json_data if isinstance(json_data, list) else [json_data]
                return json_data
            else:
                logger.info('reading content from raw text file at %s...', self.filepath)
                return f.readlines()


class IteObjectKVStoreDestination(Destination):
    """
    IteObjectKVStoreDestination represents a destination where data will be stored into different
    ITE object KVStore collection. The collection to store to will be determined by the input class.
    """
    def __init__(self, object_cls):
        self.object_cls = object_cls
        if not issubclass(self.object_cls, IteBasePersistentObject):
            raise ValueError('object_cls must be (or a subclass of) %s' % IteBasePersistentObject.__name__)

    def write(self, objects, **kwargs):
        data = []
        for obj in objects:
            ite_obj = self.object_cls.from_raw(obj)
            raw_data = ite_obj.to_raw()
            data.append(raw_data)
        self.object_cls.bulk_save(data)
        logger.info('Finished saving %s objects - count: %d', self.object_cls.__name__, len(data))


class IteProcedureInitializer(IteObjectInitializer):

    source_file_path = path.join(path.dirname(path.dirname(__file__)), 'contents', 'default', 'procedures.json')

    def __init__(self, should_keep_old=False):
        super(IteProcedureInitializer, self).__init__(
            self.source_file_path,
            IteProcedure,
            should_keep_old=should_keep_old
        )

    def should_overwrite_with_source(self, existing_procedure):
        return existing_procedure.is_original_object()

    def merge_existing_with_source_obj(self, existing_procedure, procedure_obj_from_source):
        merged_result = {}
        merged_result.update(procedure_obj_from_source)
        merged_result['favorited_by'] = existing_procedure.favorited_by
        merged_result['deployed'] = existing_procedure.deployed
        return merged_result


class IteUseCaseInitializer(IteObjectInitializer):

    source_file_path = path.join(path.dirname(path.dirname(__file__)), 'contents', 'default', 'use_cases.json')

    def __init__(self, should_keep_old=False):
        super(IteUseCaseInitializer, self).__init__(self.source_file_path, IteUseCase, should_keep_old=should_keep_old)

    def should_overwrite_with_source(self, existing_use_case):
        return existing_use_case.is_original_object()


class IteUseCaseFamilyInitializer(IteObjectInitializer):

    source_file_path = path.join(path.dirname(path.dirname(__file__)), 'contents', 'default', 'use_case_families.json')

    def __init__(self, should_keep_old=False):
        super(IteUseCaseFamilyInitializer, self).__init__(
            self.source_file_path,
            IteUseCaseFamily,
            should_keep_old=should_keep_old
        )


class IteMaturityStageInitializer(IteObjectInitializer):

    source_file_path = path.join(path.dirname(path.dirname(__file__)), 'contents', 'default', 'maturity_stages.json')

    def __init__(self, should_keep_old=False):
        super(IteMaturityStageInitializer, self).__init__(
            self.source_file_path,
            IteMaturityStage,
            should_keep_old=should_keep_old
        )
