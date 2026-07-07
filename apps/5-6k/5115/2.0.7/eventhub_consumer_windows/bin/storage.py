import errno
import os

from pathlib import Path

from azure.eventprocessorhost import AzureStorageCheckpointLeaseManager
from azure.eventprocessorhost.abstract_checkpoint_manager import AbstractCheckpointManager
from azure.eventprocessorhost.abstract_lease_manager import AbstractLeaseManager
from azure.eventprocessorhost.checkpoint import Checkpoint

# Cross-platform - fcntl is *nix-only
import portalocker

from lease import FileLease
from logger import logger

app_dir = str(Path(os.path.abspath(os.path.dirname(__file__))).parent)
OFFSET_FILE_DIRECTORY = os.path.join(app_dir, 'checkpoints')


class FileStorageCheckpointLeaseManager(AbstractCheckpointManager, AbstractLeaseManager):
    """
    Concrete implementation for storing Event Hub partition offsets in a given file.
    """
    def __init__(self, storage_dir=OFFSET_FILE_DIRECTORY, lease_renew_interval=10, lease_duration=30):
        AbstractCheckpointManager.__init__(self)
        AbstractLeaseManager.__init__(self, lease_renew_interval, lease_duration)
        self._storage_path = storage_dir
        self._locks = {}
        self.host = None

    def initialize(self, host):
        self.host = host
        # append the service bus and event hub names to the offset file prefix
        self._storage_path = os.path.join(self._storage_path, '{}_{}_'.format(
            host.eh_config.sb_name,
            host.eh_config.eh_name
        ))

    async def create_checkpoint_store_if_not_exists_async(self):
        await self.create_lease_store_if_not_exists_async()

    async def get_checkpoint_async(self, partition_id):
        lease = await self.get_lease_async(partition_id)
        checkpoint = None
        if lease and lease.offset:
            checkpoint = Checkpoint(partition_id, lease.offset, lease.sequence_number)
        return checkpoint

    async def create_checkpoint_if_not_exists_async(self, partition_id):
        checkpoint = await self.get_checkpoint_async(partition_id)
        if not checkpoint:
            await self.create_lease_if_not_exists_async(partition_id)
            checkpoint = Checkpoint(partition_id)
        return checkpoint

    async def update_checkpoint_async(self, lease, checkpoint):
        new_lease = FileLease()
        new_lease.with_source(lease)
        new_lease.offset = checkpoint.offset
        new_lease.sequence_number = checkpoint.sequence_number
        return await self.update_lease_async(new_lease)

    async def delete_checkpoint_async(self, partition_id):
        pass

    async def create_lease_store_if_not_exists_async(self):
        """
        File leases are created separately due to the locking mechanism,
        so just return True here
        """
        return True

    async def delete_lease_store_async(self):
        pass

    async def get_lease_async(self, partition_id):
        """
        Create a new lease object based on the local partition offset file

        :param partition_id: the partition ID to get a lease for
        :type partition_id: str
        :return: the created ~azure.eventprocessorhost.lease.Lease object
        :rtype: ~eventhubconsumer.file_lease.FileLease
        """
        try:
            lease = FileLease()
            lease.partition_id = partition_id
            # make sure to set the owner here so the renew
            # loop recognizes that the lease is owned by
            # the current EPH instance
            lease.owner = self.host.host_name
            if partition_id not in self._locks:
                if not await self.acquire_lease_async(lease):
                    raise IOError("No lease acquired for partition {} offset file".format(partition_id))
            f = self._locks[partition_id]
            f.seek(0)
            lease.offset, sequence_number = (f.read().strip() or '-1 0').split()
            lease.sequence_number = int(sequence_number)
            return lease
        except Exception as e:
            logger.error(repr(e))

    async def get_all_leases(self):
        """
        Return the lease info for all partitions.
        A typical implementation could just call get_lease_async() on all partitions.

        :return: A list of lease info.
        :rtype: list[~azure.eventprocessorhost.lease.Lease]
        """
        lease_futures = []
        partition_ids = await self.host.partition_manager.get_partition_ids_async()
        for partition_id in partition_ids:
            lease_futures.append(self.get_lease_async(partition_id))
        return lease_futures

    async def create_lease_if_not_exists_async(self, partition_id):
        """
        The file lease is created on the acquisition call, so just pass here
        """
        pass

    async def delete_lease_async(self, lease):
        pass

    async def acquire_lease_async(self, lease):
        """
        Acquire a lock on the partition offset file for the given lease

        :param lease: a ~azure.eventprocessorhost.lease.Lease object containing a partition ID
        :type lease: ~eventhubconsumer.file_lease.FileLease
        :return: True if the lock was successfully acquired, otherwise False
        :rtype: bool
        """
        partition = lease.partition_id
        fd = None
        try:
            fd = open('{}{}'.format(self._storage_path, str(partition)), 'a+')
            # acquire an exclusive, non-blocking lock so we fail fast if the file is in use
            portalocker.lock(fd, portalocker.LOCK_EX | portalocker.LOCK_NB)
            self._locks[partition] = fd
            logger.info("Acquired lease for partition {}".format(partition))
            return True
        except (IOError, BlockingIOError) as e:
            # expected result -  we tried to acquire a locked file
            if e.errno in (errno.EACCES, errno.EAGAIN):
                fd.close()
            logger.error(repr(e))
        return False

    async def renew_lease_async(self, lease):
        if self._locks[lease.partition_id]:
            return True
        return await self.acquire_lease_async(lease)

    async def release_lease_async(self, lease):
        """
        Release a lock on the partition offset file for the given lease

        :param lease: a ~azure.eventprocessorhost.lease.Lease object containing a partition ID
        :type lease: ~eventhubconsumer.file_lease.FileLease
        :return: True if the lock was successfully released, otherwise False
        :rtype: bool
        """
        partition = lease.partition_id
        try:
            if partition not in self._locks:
                return
            portalocker.lock(self._locks[partition], portalocker.LOCK_UN)  # release the lock
            self._locks[partition].close()
            self._locks.pop(partition)
        except IOError as e:
            logger.error(repr(e))
            return False
        return True

    async def update_lease_async(self, lease):
        """
        Write a new offset value to the file for the given lease

        :param lease: a ~azure.eventprocessorhost.lease.Lease object containing a partition ID
        :type lease: ~eventhubconsumer.file_lease.FileLease
        :return: True if the offset was successfully updated, otherwise False
        :rtype: bool
        """
        partition = lease.partition_id
        try:
            if partition not in self._locks:
                raise IOError("No lock acquired for partition {} offset file".format(partition))
            f = self._locks[partition]
            f.seek(0)
            f.truncate()
            f.write('{} {}'.format(lease.offset, lease.sequence_number))
            logger.info("INFO Updated lease:\tPartition: {}\tOffset: {}\tSequence number: {}".format(
                partition, lease.offset, lease.sequence_number))
        except Exception as e:
            logger.error(repr(e))
            return False
        return True


class StorageManagerFactory(object):

    def __init__(self):
        raise TypeError("Non-instantiable type")

    @staticmethod
    def get_instance(storage_type, *args, **kwargs):
        storage_class = FileStorageCheckpointLeaseManager
        if storage_type.lower() == 'blob':
            storage_class = AzureStorageCheckpointLeaseManager
        return storage_class(*args, **kwargs)
