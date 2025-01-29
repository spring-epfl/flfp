import logging
import time
from typing import Callable, Optional


class TimingInstance:

    def __init__(self, name, callback, disabled=False):
        self.name = name
        self.callback = callback
        self.disabled = disabled

    def __enter__(self):

        if self.disabled:
            return self

        self.start = time.time()
        return self

    def __exit__(self, *args):

        if self.disabled:
            return

        self.end = time.time()
        self.interval = self.end - self.start
        self.callback(self.name, self.interval)

        # don't suppress exceptions
        return False


class Timer:
    """

    instead of writing the ugly code:
    ```
    durations = {}
    ...
    t_code_part = time.time()
    ...code_part...
    durations['t_code_part'] = time.time() - t_code_part
    print(f"Code part took {t_code_part}s")
    ...
    ```

    Beautifully write:

    ```
    timer = Timer()
    ...

    with timer("code_part"):
        ...code_part...

    ```

    Anytime you want to retrieve the measurements, you can do:

    >>> timer.measurements
    {'code_part': [0.1]}

    """

    measurements = {}
    last = None
    log_func = None
    disabled = False

    def __init__(
        self, calibrate=False, log_func: Optional[Callable] = None, disabled=False
    ):
        self.measurements = {}
        self.logger = log_func
        self.disabled = disabled
        self.print = print

        if calibrate:
            self._calibrate()

    def _calibrate(self):

        for i in range(10):
            with self("calibration"):
                time.sleep(0.1)

    def __call__(self, name):
        return TimingInstance(name, self._store_measurement, disabled=self.disabled)

    def _store_measurement(self, name, interval):
        if name not in self.measurements:
            self.measurements[name] = []

        self.measurements[name].append(interval)
        self.last = (name, interval)

        if self.logger:
            s = f"Timer: {name} took {interval}s"
            self.logger(s)


if __name__ == "__main__":

    timer = Timer()

    with timer("test"):
        time.sleep(1)

    assert "test" in timer.measurements
    assert len(timer.measurements["test"]) == 1
    assert 1 <= timer.measurements["test"][0] <= 1.1

    with timer("test"):
        time.sleep(2)

    assert "test" in timer.measurements
    assert len(timer.measurements["test"]) == 2
    assert 1 <= timer.measurements["test"][0] <= 1.1
    assert 2 <= timer.measurements["test"][1] <= 2.1

    # nested measurements
    with timer("test"):
        with timer("nested"):
            time.sleep(1)

        with timer("nested"):
            time.sleep(2)

        with timer("nested2"):
            time.sleep(3)

    print(timer.measurements)
