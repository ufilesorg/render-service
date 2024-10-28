from singleton import Singleton


class ImaginationWorker(metaclass=Singleton):
    def __init__(self) -> None:
        self.tasks = []

    def add_task(self, task):
        self.tasks.append(task)


async def update_imagination():
    for task in ImaginationWorker().tasks:
        await task()
