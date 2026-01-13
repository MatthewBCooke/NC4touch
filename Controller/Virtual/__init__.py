"""
Virtual Hardware Components for NC4touch Chamber Testing

This package provides virtual implementations of all hardware components
to enable testing without physical chamber access.

Quick Start:
    from Virtual import VirtualChamber, VirtualChamberGUI
    
    # Create virtual chamber
    chamber = VirtualChamber()
    chamber.initialize_m0s()
    
    # Launch GUI
    gui = VirtualChamberGUI(chamber)
    gui.run()

See Virtual/README.md for complete documentation.
"""

from .VirtualM0Device import VirtualM0Device
from .VirtualBeamBreak import VirtualBeamBreak
from .VirtualBuzzer import VirtualBuzzer
from .VirtualLED import VirtualLED
from .VirtualReward import VirtualReward
from .VirtualChamber import VirtualChamber
from .VirtualChamberGUI import VirtualChamberGUI

__all__ = [
    'VirtualM0Device',
    'VirtualBeamBreak',
    'VirtualBuzzer',
    'VirtualLED',
    'VirtualReward',
    'VirtualChamber',
    'VirtualChamberGUI',
]

__version__ = '1.0.0'

