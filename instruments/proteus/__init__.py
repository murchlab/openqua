from . import daemon
from .daemon import start, stop, restart, status, request, send_scpi, set_amplitudes, set_coarse_offsets, set_fine_offsets

client_socket = None
socket = None
