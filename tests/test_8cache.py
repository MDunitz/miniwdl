import unittest
import logging
import tempfile
from .context import WDL


class TestTaskRunner(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._host_limits = WDL._util.initialize_local_docker(logging.getLogger(cls.__name__))

    def setUp(self):
        logging.basicConfig(level=logging.DEBUG, format='%(name)s %(levelname)s %(message)s')
        self._dir = tempfile.mkdtemp(prefix="miniwdl_test_cache_")

    def _test_task(self, wdl:str, inputs = None, expected_exception: Exception = None, **kwargs):
        try:
            doc = WDL.parse_document(wdl)
            assert len(doc.tasks) == 1
            doc.typecheck()
            assert len(doc.tasks[0].required_inputs.subtract(doc.tasks[0].available_inputs)) == 0
            if isinstance(inputs, dict):
                inputs = WDL.values_from_json(inputs, doc.tasks[0].available_inputs, doc.tasks[0].required_inputs)
            kwargs2 = dict(**self._host_limits)
            kwargs2.update(kwargs)
            rundir, outputs = WDL.runtime.run_local_task(doc.tasks[0], (inputs or WDL.Env.Bindings()), run_dir=self._dir, **kwargs2)
        except WDL.runtime.RunFailed as exn:
            if expected_exception:
                self.assertIsInstance(exn.__context__, expected_exception)
                return exn.__context__
            raise exn.__context__
        except Exception as exn:
            if expected_exception:
                self.assertIsInstance(exn, expected_exception)
                return exn.__context__
            raise
        if expected_exception:
            self.assertTrue(False, str(expected_exception) + " not raised")
        return WDL.values_to_json(outputs)

    def test_task_input_cache(self):
        # run task, check output matches what was stored in run_dir
        raise NotImplementedError

    def test_task_does_not_run_if_output_cached(self):
        # run task twice, check _try_task not called and TaskDockerContainer not instantiated for second run
        raise NotImplementedError