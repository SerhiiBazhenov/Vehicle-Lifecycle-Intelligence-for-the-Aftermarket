import os
import tempfile
import unittest
from unittest.mock import patch

from infrastructure.powerbi.power_bi_port_finder import PowerBIPortFinderImpl


class PowerBIPortFinderTests(unittest.TestCase):
    def test_finds_port_from_store_app_workspace_file(self):
        with tempfile.TemporaryDirectory() as local_app_data:
            port_file = os.path.join(
                local_app_data,
                'Microsoft',
                'Power BI Desktop Store App',
                'AnalysisServicesWorkspaces',
                'AnalysisServicesWorkspace_test',
                'Data',
                'msmdsrv.port.txt',
            )
            os.makedirs(os.path.dirname(port_file))
            with open(port_file, 'w', encoding='utf-16') as handle:
                handle.write('60759')

            with patch.dict(os.environ, {'LOCALAPPDATA': local_app_data}):
                port = PowerBIPortFinderImpl()._find_port_from_file()

        self.assertEqual(port, 52233)


if __name__ == '__main__':
    unittest.main()
