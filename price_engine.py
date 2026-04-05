import threading
from datetime import datetime, timedelta
from config import PRICE_UPDATE_INTERVAL, KRASH_DURATION
from database import update_all_prices, set_setting, get_setting

class PriceEngine:
    """Engine that manages price fluctuations"""
    
    def __init__(self, socketio):
        self.socketio = socketio
        self.running = False
        self.thread = None
        self.timer = PRICE_UPDATE_INTERVAL
        self.krash_active = False
        self.krash_end_time = None
        self.lock = threading.Lock()
        
    def start(self):
        """Start the price engine"""
        if self.running:
            return
            
        self.running = True
        self.timer = PRICE_UPDATE_INTERVAL
        
        # Check if krash is still active from previous session
        krash_end = get_setting('krash_end_time')
        if krash_end:
            try:
                krash_end_time = datetime.fromisoformat(krash_end)
                if krash_end_time > datetime.now():
                    self.krash_active = True
                    self.krash_end_time = krash_end_time
            except (ValueError, TypeError):
                set_setting('krash_end_time', '')
        
        self.thread = self.socketio.start_background_task(self._run_loop)
        
    def stop(self):
        """Stop the price engine"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
            
    def _run_loop(self):
        """Main loop that updates prices every interval"""
        while self.running:
            self.socketio.sleep(1)

            try:
                with self.lock:
                    # Check if krash should end
                    if self.krash_active and self.krash_end_time:
                        if datetime.now() >= self.krash_end_time:
                            self.krash_active = False
                            self.krash_end_time = None
                            set_setting('krash_end_time', '')
                            drinks = update_all_prices(krash_mode=False)
                            self._emit_update(drinks, 'krash_ended')
                            self.timer = PRICE_UPDATE_INTERVAL
                            continue

                    # Decrement timer
                    self.timer -= 1

                    # Emit timer update
                    self.socketio.emit('timer_update', {
                        'timer': self.timer,
                        'krash_active': self.krash_active,
                        'krash_remaining': self._get_krash_remaining()
                    })

                    # Update prices when timer reaches 0
                    if self.timer <= 0:
                        if not self.krash_active:
                            drinks = update_all_prices(krash_mode=False)
                            self._emit_update(drinks, 'price_update')
                        self.timer = PRICE_UPDATE_INTERVAL
            except Exception as e:
                print(f"[PriceEngine] Error in update loop: {e}")
                # Continue running despite errors
                    
    def _emit_update(self, drinks, event_type):
        """Emit price update to all clients"""
        # Group drinks by type
        grouped = {}
        for drink in drinks:
            drink_type = drink['type']
            if drink_type not in grouped:
                grouped[drink_type] = []
            grouped[drink_type].append(drink)
            
        self.socketio.emit('prices_update', {
            'event': event_type,
            'drinks': grouped,
            'timestamp': datetime.now().isoformat()
        })
        
    def _get_krash_remaining(self):
        """Get remaining krash time in seconds"""
        if not self.krash_active or not self.krash_end_time:
            return 0
        remaining = (self.krash_end_time - datetime.now()).total_seconds()
        return max(0, int(remaining))
        
    def trigger_krash(self, duration=None):
        """Trigger the KRASH mode"""
        if duration is None:
            duration = KRASH_DURATION
            
        with self.lock:
            self.krash_active = True
            self.krash_end_time = datetime.now() + timedelta(seconds=duration)
            set_setting('krash_end_time', self.krash_end_time.isoformat())
            
            # Update all prices to krash prices
            drinks = update_all_prices(krash_mode=True)
            self._emit_update(drinks, 'krash_started')
            
            # Emit krash notification
            self.socketio.emit('krash', {
                'active': True,
                'duration': duration,
                'end_time': self.krash_end_time.isoformat()
            })
            
            return True
            
    def stop_krash(self):
        """Stop the KRASH mode early"""
        with self.lock:
            if not self.krash_active:
                return False
                
            self.krash_active = False
            self.krash_end_time = None
            set_setting('krash_end_time', '')
            
            # Update prices to exit krash
            drinks = update_all_prices(krash_mode=False)
            self._emit_update(drinks, 'krash_ended')
            self.timer = PRICE_UPDATE_INTERVAL
            
            self.socketio.emit('krash', {
                'active': False
            })
            
            return True
            
    def get_status(self):
        """Get current engine status"""
        return {
            'timer': self.timer,
            'interval': PRICE_UPDATE_INTERVAL,
            'krash_active': self.krash_active,
            'krash_remaining': self._get_krash_remaining()
        }
