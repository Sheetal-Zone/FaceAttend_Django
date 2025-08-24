from django.core.management.base import BaseCommand
from django.conf import settings
from attendance.camera_processor import camera_manager
import time
import signal
import sys


class Command(BaseCommand):
    help = 'Start the face detection system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--camera-id',
            type=int,
            help='Start detection for a specific camera ID'
        )
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Run in daemon mode'
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting face detection system...')
        )
        
        try:
            # Start camera processing
            if options['camera_id']:
                # Start specific camera
                camera_manager.start_camera_by_id(options['camera_id'])
                self.stdout.write(
                    self.style.SUCCESS(f'Started camera {options["camera_id"]}')
                )
            else:
                # Start all cameras
                camera_manager.start_all_cameras()
                self.stdout.write(
                    self.style.SUCCESS('Started all camera streams')
                )
            
            if not options['daemon']:
                # Run in foreground
                self.stdout.write('Detection system running. Press Ctrl+C to stop.')
                self._run_foreground()
            else:
                # Run in background
                self.stdout.write('Detection system started in background.')
                self._run_background()
                
        except KeyboardInterrupt:
            self.stdout.write('\nStopping detection system...')
            camera_manager.stop_all_cameras()
            self.stdout.write(
                self.style.SUCCESS('Detection system stopped.')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error: {str(e)}')
            )
            sys.exit(1)

    def _run_foreground(self):
        """Run detection in foreground with signal handling."""
        def signal_handler(signum, frame):
            self.stdout.write('\nReceived signal to stop...')
            camera_manager.stop_all_cameras()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    def _run_background(self):
        """Run detection in background."""
        # In background mode, just start and exit
        # The camera manager will keep running
        pass
