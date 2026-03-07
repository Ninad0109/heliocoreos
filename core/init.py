#!/usr/bin/env python3
import sys
sys.path.append('/home/pi/heliocoreos')
from core.boot_manager import BootManager
from core.heliocore_shell import HelioCoreShell

def main():
    boot = BootManager()
    
    if boot.boot():
        # Boot successful, launch shell
        shell = HelioCoreShell()
        shell.run()
        
        # Shell exited, shutdown
        boot.shutdown()
    else:
        print("\n[ERROR] Boot failed. Check logs for details.")
        sys.exit(1)

if __name__ == '__main__':
    main()
