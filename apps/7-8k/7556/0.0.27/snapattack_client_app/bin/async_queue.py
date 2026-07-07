import asyncio
import typing as t


def apply_asyncio_queue(
    awaitables: t.Iterable[t.Awaitable], max_concurrent: int, exception_callback: t.Optional[t.Callable[..., t.Any]],
    result_callback: t.Optional[t.Callable[..., t.Any]], **result_callback_kwargs: t.Dict[str, t.Any]
):
    """Processes a group of asyncio tasks in batches using a worker queue"""
    async def _queue_worker(queue: asyncio.Queue):
        while True:
            future = await queue.get()
            try:
                result = await future
                if result_callback:
                    result_callback(result, **result_callback_kwargs)
            except Exception as ex:
                # Need to handle here so as to not short-circuit processing the remaining futures.
                if exception_callback:
                    exception_callback(ex)
                else:
                    print(f'Unhandled Exception received from async future: {str(ex)}')
            finally:
                queue.task_done()

    async def _process_tasks():
        queue = asyncio.Queue()
        for task in awaitables:
            queue.put_nowait(task)
        worker_tasks = []
        for i in range(max_concurrent):
            task = asyncio.create_task(_queue_worker(queue))
            worker_tasks.append(task)
        await queue.join()
        for task in worker_tasks:
            task.cancel()
        await asyncio.gather(*worker_tasks, return_exceptions=True)

    asyncio.run(_process_tasks())
