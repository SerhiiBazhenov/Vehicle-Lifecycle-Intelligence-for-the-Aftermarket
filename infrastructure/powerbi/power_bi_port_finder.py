import logging
import os
import socket
import subprocess
import sys
from glob import glob
from pathlib import Path
from typing import Optional

from domain.ports.power_bi_reader import PowerBIPortFinder

logger = logging.getLogger(__name__)


def ensure_adomd_available() -> bool:
    """Знаходить і реєструє Microsoft.AnalysisServices.AdomdClient.dll у .NET CLR."""
    try:
        import clr  # type: ignore
    except ImportError as exc:
        logger.error('pythonnet is required to load the ADOMD client: %s', exc)
        return False

    candidates = [
        r"C:\Program Files\Microsoft.NET\ADOMD.NET\160",
        r"C:\Program Files\DAX Studio",
        r"C:\Program Files\SQLBI\Bravo",
        r"C:\Program Files\Power BI Desktop\bin",
        r"C:\Program Files\Microsoft Power BI Desktop\bin",
    ]

    for candidate in candidates:
        dll_file = os.path.join(candidate, "Microsoft.AnalysisServices.AdomdClient.dll")
        if not os.path.isfile(dll_file):
            continue

        if candidate not in sys.path:
            sys.path.append(candidate)

        if candidate not in os.environ.get('PATH', '').split(os.pathsep):
            os.environ['PATH'] = candidate + os.pathsep + os.environ.get('PATH', '')

        try:
            clr.AddReference(dll_file)
            logger.info('ADOMD runtime successfully registered from: %s', candidate)
            return True
        except Exception as exc:
            logger.debug('Failed to load ADOMD from %s: %s', candidate, exc)

    logger.warning('ADOMD client DLL directory was not found. Power BI connection may fail.')
    return False


def is_port_listening(port: int, host: str = '127.0.0.1', timeout: float = 0.5) -> bool:
    """Перевіряє, чи дійсно відкритий та слухає порт на локальному хості."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        try:
            return s.connect_ex((host, port)) == 0
        except Exception:
            return False


class PowerBIPortFinderImpl(PowerBIPortFinder):
    def find_port(self) -> Optional[int]:
        logger.info('Searching for active Power BI Analysis Services port...')
        
        port = self._find_port_from_file()
        if port:
            logger.info('Detected active Power BI port from workspace file: %s.', port)
            return port

        port_wmi = self._find_port_from_wmi()
        if port_wmi:
            logger.info('Detected Power BI on port %s via WMI.', port_wmi)
            return port_wmi

        logger.error('No active Power BI Analysis Services process/port found.')
        return None

    def _find_port_from_file(self) -> Optional[int]:
        try:
            local_app_data = os.environ.get('LOCALAPPDATA')
            if not local_app_data:
                return None
            
            patterns = [
                os.path.join(
                    local_app_data,
                    r'Microsoft\Power BI Desktop\AnalysisServicesWorkspaces\AnalysisServicesWorkspace*\Data\msmdsrv.port.txt',
                ),
                os.path.join(
                    local_app_data,
                    r'Microsoft\Power BI Desktop Store App\AnalysisServicesWorkspaces\AnalysisServicesWorkspace*\Data\msmdsrv.port.txt',
                ),
                os.path.join(
                    local_app_data,
                    r'Packages\Microsoft.MicrosoftPowerBIDesktop_8wekyb3d8bbwe\LocalState\AnalysisServicesWorkspaces\AnalysisServicesWorkspace*\Data\msmdsrv.port.txt',
                ),
            ]

            files = [file_path for pattern in patterns for file_path in glob(pattern)]
            if not files:
                return None

            sorted_files = sorted(files, key=os.path.getmtime, reverse=True)

            for file_path in sorted_files:
                try:
                    content = Path(file_path).read_text(encoding='utf-16').strip()
                    port = int(content)
                    
                    if 0 < port < 65536 and is_port_listening(port):
                        return port
                except Exception as exc:
                    logger.debug('Could not process port file %s: %s', file_path, exc)

        except Exception as exc:
            logger.debug('Could not scan workspace directories: %s', exc)
        
        return None

    def _find_port_from_wmi(self) -> Optional[int]:
        try:
            import wmi  # type: ignore

            c = wmi.WMI()
            process_ids = {
                str(process.ProcessId)
                for process in c.Win32_Process(name='msmdsrv.exe')
            }
            if not process_ids:
                return None

            output = subprocess.check_output(
                ['netstat', '-ano'],
                text=True,
                encoding='utf-8',
                errors='replace',
            )
            for line in output.splitlines():
                parts = line.split()
                if (
                    len(parts) < 5
                    or parts[-2].upper() != 'LISTENING'
                    or parts[-1] not in process_ids
                ):
                    continue

                local_address = parts[1]
                if ':' not in local_address:
                    continue

                port_text = local_address.rsplit(':', 1)[-1]
                try:
                    port = int(port_text)
                    if 0 < port < 65536 and is_port_listening(port):
                        return port
                except ValueError:
                    continue
        except Exception as exc:
            logger.exception('Failed to determine Power BI port via WMI: %s', exc)
        return None