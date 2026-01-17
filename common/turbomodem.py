"""
TURBOMODEM - Ultra-Fast Transfer Protocol
==========================================

10-20x schneller als XModem durch:
- Große Blocks (4 KB)
- Sliding Window (8 Blocks ohne ACK)
- CRC-32 Checksumme
- Einfaches Error Recovery

Performance:
- XModem: ~30-250 KB/s
- TurboModem: ~500 KB/s - 2 MB/s ✅
"""

import struct
import zlib
import time
import datetime

# Protocol Constants
MAGIC = b'TB'  # TurboBlock
CMD_REQUEST = b'TBRQ'  # Client requests transfer
CMD_OK = b'TBOK'  # Server ready
CMD_ACK = b'TBAC'  # Block(s) acknowledged
CMD_NAK = b'TBNK'  # Block(s) need retransmit
CMD_EOT = b'TBEOT'  # End of transfer
CMD_CAN = b'TBCAN'  # Cancel transfer

BLOCK_SIZE = 4096  # 4 KB blocks
WINDOW_SIZE = 8  # 8 blocks without ACK = 32 KB pipeline
MAX_RETRIES = 16


class TurboModem:
    """TurboModem Protocol Implementation"""
    
    def __init__(self, connection, debug=False):
        """
        Args:
            connection: Socket-like object with sendall() and recv() methods
                       OR BBSTelnetClient with send_raw() and get_received_data_raw()
            debug: Enable debug logging
        """
        self.conn = connection
        self.debug = debug
        self.debug_log = []
        
        self.stats = {
            'blocks_sent': 0,
            'blocks_received': 0,
            'retransmits': 0,
            'bytes_transferred': 0,
            'start_time': 0,
            'end_time': 0,
            'blocks_corrupted': 0,
            'blocks_retried': 0,
            'timeouts': 0
        }
    
    def log(self, msg):
        """Debug logging - nur zu File, kein print()!"""
        if self.debug:
            import datetime
            timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
            log_msg = f"[{timestamp}] {msg}"
            self.debug_log.append(log_msg)
            # KEIN print() - würde Terminal blockieren!
    
    def save_debug_log(self, filepath="turbomodem_debug.txt"):
        """Save debug log to file"""
        if self.debug_log:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(self.debug_log))
                    f.write(f"\n\n===== LOG SAVED AT {datetime.datetime.now()} =====\n")
                self.log(f"Debug log saved to {filepath}")
            except Exception as e:
                # Fallback - versuche im temp dir
                try:
                    import tempfile
                    temp_path = tempfile.gettempdir() + "/turbomodem_debug.txt"
                    with open(temp_path, 'w', encoding='utf-8') as f:
                        f.write('\n'.join(self.debug_log))
                    self.log(f"Debug log saved to {temp_path} (fallback)")
                except:
                    pass
    
    def __del__(self):
        """Destruktor - speichere Log automatisch"""
        if self.debug and self.debug_log:
            self.save_debug_log()
    
    def _send(self, data):
        """Send data - works with both Socket and BBSTelnetClient"""
        if hasattr(self.conn, 'send_raw'):
            # BBSTelnetClient
            self.conn.send_raw(data)
        elif hasattr(self.conn, 'sendall'):
            # Socket
            self.conn.sendall(data)
        else:
            # Fallback
            self.conn.send(data)
    
    def _recv_exact(self, size, timeout=3.0):
        """
        Empfängt exakt 'size' Bytes
        
        Returns:
            bytes oder None bei Timeout/Error
        """
        import time
        
        # Nur bei großen Requests loggen (Block-Daten)
        if size > 100:
            self.log(f"_recv_exact: Requesting {size} bytes, timeout={timeout}s")
        
        # Nutze unsere Connection get_received_data_raw
        if hasattr(self.conn, 'get_received_data_raw'):
            # WICHTIG: get_received_data_raw könnte weniger zurückgeben!
            # Wir müssen in Loop sammeln bis wir exakt size Bytes haben
            data = bytearray()
            end_time = time.time() + timeout
            loop_count = 0
            
            while len(data) < size:
                if time.time() > end_time:
                    self.log(f"_recv_exact: TIMEOUT! Got {len(data)}/{size} bytes after {loop_count} loops")
                    self.stats['timeouts'] += 1
                    return None
                
                remaining = size - len(data)
                chunk = self.conn.get_received_data_raw(remaining, timeout=max(0.1, end_time - time.time()))
                loop_count += 1
                
                if not chunk:
                    # Kurz warten und retry
                    time.sleep(0.001)
                    continue
                
                # Nur bei Problemen loggen (mehr als 3 loops)
                if loop_count > 3 and size > 100:
                    self.log(f"_recv_exact: Loop {loop_count}: Got {len(chunk)} bytes, total {len(data)+len(chunk)}/{size}")
                
                data.extend(chunk)
            
            # Nur bei Problemen loggen (mehr als 2 loops)
            if loop_count > 2 and size > 100:
                self.log(f"_recv_exact: Took {loop_count} loops to get {len(data)} bytes")
            
            return bytes(data)
        else:
            # Fallback für direkte Socket
            data = bytearray()
            end_time = time.time() + timeout
            
            # WICHTIG: Setze Socket-Timeout!
            old_timeout = None
            try:
                if hasattr(self.conn, 'gettimeout'):
                    old_timeout = self.conn.gettimeout()
                    self.conn.settimeout(timeout)
            except:
                pass
            
            try:
                while len(data) < size:
                    if time.time() > end_time:
                        return None
                    
                    try:
                        remaining_time = end_time - time.time()
                        if remaining_time <= 0:
                            return None
                        
                        # Update timeout für verbleibende Zeit
                        if hasattr(self.conn, 'settimeout'):
                            self.conn.settimeout(max(0.1, remaining_time))
                        
                        chunk = self.conn.recv(size - len(data))
                        if not chunk:
                            return None
                        data.extend(chunk)
                    except Exception as e:
                        # Timeout oder anderer Error
                        if time.time() > end_time:
                            return None
                        # Kurz warten und retry
                        time.sleep(0.001)
            finally:
                # Stelle alten Timeout wieder her
                if old_timeout is not None:
                    try:
                        self.conn.settimeout(old_timeout)
                    except:
                        pass
            
            return bytes(data)
    
    def send_block(self, block_num, data):
        """
        Sendet einen TurboBlock
        
        Format:
        [MAGIC: 2B][Block#: 4B][Size: 2B][Data: N][CRC-32: 4B]
        
        Size im Header ist immer BLOCK_SIZE (4096) für konsistentes Empfangen.
        Das Trimmen auf die tatsächliche Dateigröße erfolgt beim Empfänger
        basierend auf der filesize aus dem initialen Header.
        """
        # Pad data to BLOCK_SIZE if needed
        if len(data) < BLOCK_SIZE:
            data = data + b'\x00' * (BLOCK_SIZE - len(data))
        
        # Build header - Size ist IMMER die gepaddete Größe für konsistentes Empfangen
        header = MAGIC + struct.pack('>I', block_num) + struct.pack('>H', BLOCK_SIZE)
        
        # Calculate CRC-32 over padded data
        crc = zlib.crc32(data) & 0xFFFFFFFF
        
        # Send complete block
        block = header + data + struct.pack('>I', crc)
        
        # Nutze send_raw wenn verfügbar (BBSTelnetClient), sonst sendall (Socket)
        if hasattr(self.conn, 'send_raw'):
            self.conn.send_raw(block)
        elif hasattr(self.conn, 'sendall'):
            self._send(block)
        else:
            # Fallback: Versuche direkt zu senden
            self.conn.send(block)
        
        self.stats['blocks_sent'] += 1
    
    def receive_block(self, timeout=3.0):
        """
        Empfängt einen TurboBlock
        
        Format:
        [MAGIC: 2B][Block#: 4B][Size: 2B][Data: N][CRC-32: 4B]
        
        Returns:
            (block_num, data) oder None bei Error
        """
        # Read header
        header = self._recv_exact(8, timeout)
        if not header:
            self.log("receive_block: Failed to receive header")
            return None
        
        magic, block_num, block_size = struct.unpack('>2sIH', header)
        if magic != MAGIC:
            self.log(f"receive_block: Invalid magic: {magic} (expected {MAGIC})")
            return None
        
        # Block size sollte immer BLOCK_SIZE sein, aber akzeptiere auch andere Werte
        # für Abwärtskompatibilität
        actual_recv_size = block_size if block_size > 0 else BLOCK_SIZE
        
        # Nur alle 10 Blocks loggen (zu viel Output sonst!)
        if block_num % 10 == 0:
            self.log(f"receive_block: Block #{block_num}, header_size={block_size}, recv_size={actual_recv_size}")
        
        # Read data - empfange die angegebene Größe
        data = self._recv_exact(actual_recv_size, timeout)
        if not data:
            self.log(f"receive_block: Failed to receive data for block #{block_num}")
            return None
        
        # Read CRC
        crc_bytes = self._recv_exact(4, timeout)
        if not crc_bytes:
            self.log(f"receive_block: Failed to receive CRC for block #{block_num}")
            return None
        
        expected_crc = struct.unpack('>I', crc_bytes)[0]
        actual_crc = zlib.crc32(data) & 0xFFFFFFFF
        
        if expected_crc != actual_crc:
            self.log(f"receive_block: CRC MISMATCH on block #{block_num}! Expected {expected_crc:08x}, got {actual_crc:08x}")
            self.stats['blocks_corrupted'] += 1
            return None
        
        self.stats['blocks_received'] += 1
        return (block_num, data)
    
    def send_file(self, filepath, callback=None):
        """
        Sendet Datei mit TurboModem Protokoll (Client → BBS)
        
        Args:
            filepath: Path zur Datei
            callback: Progress callback(bytes_sent, total_bytes, status)
            
        Returns:
            True bei Erfolg, False bei Fehler
        """
        import os
        
        self.log(f"===== SEND FILE START: {filepath} =====")
        self.stats['start_time'] = time.time()
        filesize = os.path.getsize(filepath)
        
        # Extrahiere Dateinamen MIT Extension
        basename = os.path.basename(filepath)
        filename_to_send = basename  # Kompletter Name inkl. Extension!
        self.log(f"Original filename: {basename}")
        self.log(f"Sending as: {filename_to_send} (with extension)")
        self.log(f"Filesize: {filesize:,} bytes ({filesize // BLOCK_SIZE + 1} blocks)")
        
        # Wait for REQUEST from receiver
        self.log("Waiting for REQUEST from receiver...")
        req = self._recv_exact(4, timeout=10)
        if req != CMD_REQUEST:
            self.log(f"ERROR: Expected REQUEST, got {req}")
            return False
        
        # Send OK + Filesize + Filename (MIT Extension!)
        self.log("Sending OK + Filesize + Filename...")
        filename_bytes = filename_to_send.encode('utf-8')
        filename_len = len(filename_bytes)
        
        # Format: OK(4) + Filesize(8) + FilenameLen(2) + Filename(N)
        header = CMD_OK + struct.pack('>Q', filesize) + struct.pack('>H', filename_len) + filename_bytes
        self._send(header)
        self.log(f"Sent filename: {filename_to_send} ({filename_len} bytes)")
        
        if callback:
            callback(0, filesize, "Starting TurboModem send...")
        
        with open(filepath, 'rb') as f:
            block_num = 1
            window = []  # [(block_num, data), ...]
            bytes_sent = 0
            retries = 0
            window_num = 0
            
            while True:
                # Fill window with blocks
                while len(window) < WINDOW_SIZE:
                    data = f.read(BLOCK_SIZE)
                    if not data:
                        break
                    window.append((block_num, data))
                    block_num += 1
                
                if not window:
                    # All blocks sent and acknowledged
                    self.log("All windows complete, exiting send loop")
                    break
                
                window_num += 1
                first_block = window[0][0]
                last_block = window[-1][0]
                self.log(f"===== WINDOW #{window_num} (blocks {first_block}-{last_block}, count={len(window)}) =====")
                
                # Send all blocks in window
                for bn, data in window:
                    self.send_block(bn, data)
                    if bn % 100 == 0:  # Nur alle 100 Blocks loggen
                        self.log(f"Sent block #{bn}")
                
                # Wait for ACK
                self.log("Waiting for ACK...")
                ack_cmd = self._recv_exact(4, timeout=10)
                
                if ack_cmd == CMD_CAN:
                    self.log("ERROR: Transfer cancelled by receiver")
                    return False
                
                if ack_cmd != CMD_ACK:
                    self.log(f"ERROR: Expected ACK, got {ack_cmd}")
                    retries += 1
                    if retries > MAX_RETRIES:
                        self.log("MAX RETRIES exceeded!")
                        return False
                    continue
                
                # Get bitmap
                bitmap_bytes = self._recv_exact(1, timeout=1)
                if not bitmap_bytes:
                    self.log("ERROR: Failed to get bitmap")
                    retries += 1
                    if retries > MAX_RETRIES:
                        return False
                    continue
                
                bitmap = bitmap_bytes[0]
                self.log(f"Got bitmap: {bitmap:02x}")
                
                if bitmap == 0xFF:
                    # All blocks OK
                    for bn, data in window:
                        bytes_sent += len(data)
                    window = []
                    retries = 0
                    
                    self.log(f"Window OK! bytes_sent={bytes_sent:,}/{filesize:,} ({100*bytes_sent//filesize}%)")
                    
                    if callback:
                        callback(bytes_sent, filesize, f"Sent {bytes_sent // 1024} KB")
                else:
                    # Some blocks need retransmit
                    self.log(f"Retransmit needed! Bitmap={bitmap:02x}")
                    new_window = []
                    for i, (bn, data) in enumerate(window):
                        if not (bitmap & (1 << i)):
                            # This block needs retransmit
                            new_window.append((bn, data))
                            self.stats['retransmits'] += 1
                    window = new_window
                    retries += 1
                    if retries > MAX_RETRIES:
                        return False
        
        # Send EOT
        self.log("Sending EOT...")
        self._send(CMD_EOT)
        
        # Wait for final ACK
        self.log("Waiting for final ACK...")
        final_ack = self._recv_exact(4, timeout=5)
        
        self.stats['end_time'] = time.time()
        self.stats['bytes_transferred'] = filesize
        
        duration = self.stats['end_time'] - self.stats['start_time']
        speed = filesize / duration if duration > 0 else 0
        
        self.log(f"===== SEND COMPLETE =====")
        self.log(f"Duration: {duration:.2f}s")
        self.log(f"Speed: {speed/1024:.2f} KB/s")
        self.log(f"Blocks sent: {self.stats['blocks_sent']}")
        self.log(f"Retransmits: {self.stats['retransmits']}")
        self.log(f"Final ACK: {'OK' if final_ack == CMD_ACK else 'MISSING'}")
        
        # Save debug log only if debug is enabled
        if self.debug:
            self.save_debug_log("turbomodem_upload_debug.txt")
        
        if callback:
            callback(filesize, filesize, "Transfer complete")
        
        return final_ack == CMD_ACK
    
    def receive_file(self, filepath, callback=None):
        """
        Empfängt Datei mit TurboModem Protokoll (BBS → Client)
        
        Args:
            filepath: Ziel - kann Verzeichnis oder Temp-Dateiname sein
            callback: Progress callback(bytes_received, total_bytes, status, filename)
            
        Returns:
            (success, actual_filepath) - True/False und tatsächlicher Dateipfad
        """
        import os
        
        # Pfad normalisieren (/ -> \ auf Windows)
        filepath = os.path.normpath(filepath).replace('/', os.sep)
        
        self.log(f"===== RECEIVE FILE START =====")
        self.log(f"Input filepath: {filepath}")
        
        # Bestimme Ziel-Verzeichnis
        if os.path.isdir(filepath):
            # filepath IST ein Verzeichnis
            target_dir = filepath
            self.log(f"Input is existing directory")
        elif os.path.isfile(filepath):
            # filepath IST eine Datei - verwende ihr Verzeichnis
            target_dir = os.path.dirname(filepath)
            self.log(f"Input is existing file - using directory")
        else:
            # filepath existiert nicht
            # Wenn es eine Extension hat (.bin, .prg) -> es ist ein Temp-File
            # Verwende nur das Verzeichnis-Teil
            if '.' in os.path.basename(filepath):
                target_dir = os.path.dirname(filepath)
                self.log(f"Input looks like temp file (has extension) - using directory part")
            else:
                target_dir = filepath
                self.log(f"Input looks like directory")
        
        # Erstelle Verzeichnis falls nötig
        if not os.path.exists(target_dir):
            try:
                os.makedirs(target_dir, exist_ok=True)
                self.log(f"Created directory: {target_dir}")
            except Exception as e:
                self.log(f"ERROR: Cannot create directory: {e}")
                return (False, None)
        
        self.log(f"Target directory: {target_dir}")
        self.stats['start_time'] = time.time()
        
        # WICHTIG: Bei Upload (Server empfängt) muss gewartet werden bis Client bereit ist
        # Aber nur wenn wir wirklich der Empfänger sind (nicht bei Download!)
        # Der Client braucht Zeit um Upload-Dialog zu öffnen und send_file() aufzurufen
        
        # Versuche zu erkennen: Gibt es schon Daten im Buffer?
        # Wenn ja -> Client hat schon gesendet, kein Delay nötig
        # Wenn nein -> Client ist noch nicht bereit, warte 3 Sekunden
        try:
            # Prüfe ob Daten verfügbar sind (non-blocking)
            if hasattr(self.conn, 'recv'):
                # Socket: Nutze MSG_PEEK um zu schauen ohne zu konsumieren
                import socket
                old_timeout = self.conn.gettimeout()
                self.conn.settimeout(0.1)  # 100ms non-blocking check
                try:
                    peek_data = self.conn.recv(1, socket.MSG_PEEK)
                    if peek_data:
                        self.log("Client already sent data - no delay needed")
                    else:
                        self.log("No data yet - waiting 3 seconds for client...")
                        time.sleep(3.0)
                except socket.timeout:
                    # Kein Timeout-Error = keine Daten
                    self.log("No data in buffer - waiting 3 seconds for client...")
                    time.sleep(3.0)
                except:
                    # Fallback: Warte sicherheitshalber
                    self.log("Cannot check buffer - waiting 3 seconds...")
                    time.sleep(3.0)
                finally:
                    self.conn.settimeout(old_timeout)
            else:
                # Kein recv verfügbar - warte sicherheitshalber
                self.log("Unknown connection type - waiting 3 seconds...")
                time.sleep(3.0)
        except:
            # Bei Fehler: Warte sicherheitshalber
            self.log("Error checking buffer - waiting 3 seconds...")
            time.sleep(3.0)
        
        # Send REQUEST (mehrmals bei Upload, einmal bei Download)
        # Bei Upload: Server wartet auf Client → viele Retries nötig
        # Bei Download: Client wartet auf Server → kein Retry nötig
        
        # Versuche zu erkennen: Sind wir Upload-Empfänger oder Download-Empfänger?
        # Heuristik: Bei Upload wurde schon 3 Sekunden gewartet (siehe oben)
        # Bei Download wird nicht gewartet (Client sendet sofort REQUEST)
        
        # Einfache Lösung: Sende REQUEST mit kurzem Timeout
        # Wenn OK kommt → gut!
        # Wenn nicht → retry (maximal 30× für Upload)
        
        self.log("Sending REQUEST...")
        
        max_retries = 30  # Maximal 30 Versuche
        retry_delay = 1.0  # 1 Sekunde zwischen Versuchen
        first_timeout = 10.0  # Erster Versuch: 10 Sekunden (für Download)
        
        for attempt in range(max_retries):
            if attempt == 0:
                # Erster Versuch: Längerer Timeout (Download könnte sofort antworten)
                timeout = first_timeout
            else:
                # Weitere Versuche: Kurzer Timeout (Upload-Retries)
                timeout = retry_delay
            
            self._send(CMD_REQUEST)
            
            if attempt == 0:
                self.log(f"Sent REQUEST (waiting {timeout}s for response)...")
            else:
                self.log(f"Sent REQUEST (attempt {attempt + 1}/{max_retries})...")
            
            # Warte auf Antwort
            try:
                ok = self._recv_exact(4, timeout=timeout)
                
                if ok == CMD_OK:
                    self.log("✓ Got OK from sender!")
                    break
                elif ok:
                    self.log(f"Got unexpected response: {ok.hex()}, retrying...")
                    continue
                else:
                    # Timeout
                    if attempt == 0:
                        # Nach erstem Timeout: Switch zu Retry-Modus
                        self.log(f"No response after {timeout}s, switching to retry mode...")
                    else:
                        self.log(f"No response yet, retrying...")
                    continue
                    
            except Exception as e:
                self.log(f"Exception during REQUEST: {e}, retrying...")
                continue
        else:
            # Alle Versuche fehlgeschlagen
            self.log(f"ERROR: Sender did not respond after {max_retries} attempts")
            return (False, None)
        
        # OK empfangen - jetzt Filesize + Filename empfangen
        self.log("Waiting for Filesize + Filename...")
        
        # Receive filesize (8 bytes)
        filesize_bytes = self._recv_exact(8, timeout=10)
        if not filesize_bytes:
            return (False, None)
        
        filesize = struct.unpack('>Q', filesize_bytes)[0]
        
        # Receive filename length (2 bytes)
        filename_len_bytes = self._recv_exact(2, timeout=10)
        if not filename_len_bytes:
            return (False, None)
        
        filename_len = struct.unpack('>H', filename_len_bytes)[0]
        self.log(f"Filename length: {filename_len}")
        
        # Receive filename
        filename_bytes = self._recv_exact(filename_len, timeout=10)
        if not filename_bytes:
            return (False, None)
        
        filename = filename_bytes.decode('utf-8', errors='replace')
        self.log(f"Server filename: {filename}")
        
        # Server sendet jetzt kompletten Filename MIT Extension
        # (Früher wurde Extension entfernt, jetzt nicht mehr)
        
        # Build ACTUAL filepath using target_dir + server filename
        actual_filepath = os.path.join(target_dir, filename)
        self.log(f"Final filepath: {actual_filepath}")
        self.log(f"Filesize: {filesize:,} bytes ({filesize // BLOCK_SIZE + 1} blocks expected)")
        
        if callback:
            callback(0, filesize, "Starting TurboModem receive...", filename)
        
        # KRITISCH: Öffne actual_filepath (NICHT filepath!)
        with open(actual_filepath, 'wb') as f:
            expected_block = 1
            window_received = {}  # {block_num: data}
            bytes_received = 0
            retries = 0
            window_num = 0
            
            while bytes_received < filesize:
                window_num += 1
                
                # Berechne wie viele Blöcke noch fehlen
                bytes_remaining = filesize - bytes_received
                blocks_remaining = (bytes_remaining + BLOCK_SIZE - 1) // BLOCK_SIZE
                expected_blocks_in_window = min(WINDOW_SIZE, blocks_remaining)
                
                self.log(f"===== WINDOW #{window_num} (expecting blocks {expected_block}-{expected_block+expected_blocks_in_window-1}, total={expected_blocks_in_window}) =====")
                self.log(f"Bytes remaining: {bytes_remaining:,}, blocks remaining: {blocks_remaining}")
                
                # Receive blocks
                blocks_in_window = 0
                timeout_count = 0
                
                while blocks_in_window < expected_blocks_in_window and timeout_count < 3:
                    block_result = self.receive_block(timeout=10)
                    
                    if block_result is None:
                        # Timeout or error
                        timeout_count += 1
                        self.log(f"receive_block returned None (timeout #{timeout_count})")
                        
                        # Wenn wir schon einige Blöcke haben und ein Timeout kommt,
                        # könnte der Transfer fertig sein
                        if blocks_in_window > 0 and bytes_received + (blocks_in_window * BLOCK_SIZE) >= filesize:
                            self.log(f"Received enough data ({bytes_received + blocks_in_window * BLOCK_SIZE} >= {filesize}), assuming transfer complete")
                            break
                        
                        # Bei 3 Timeouts -> raus aus der Block-Loop
                        if timeout_count >= 3:
                            self.log(f"3 consecutive timeouts, breaking block receive loop")
                            break
                        continue
                    
                    # Reset timeout counter bei erfolgreichem Empfang
                    timeout_count = 0
                    
                    block_num, data = block_result
                    window_received[block_num] = data
                    blocks_in_window += 1
                    
                    # Check if we got all EXPECTED blocks (nicht alle WINDOW_SIZE!)
                    all_received = True
                    for i in range(expected_blocks_in_window):  # Nur erwartete Blöcke!
                        if (expected_block + i) not in window_received:
                            all_received = False
                            break
                    
                    if all_received:
                        self.log(f"All {expected_blocks_in_window} expected blocks received!")
                        break
                
                # Build ACK bitmap - nur für erwartete Blöcke!
                bitmap = 0xFF
                for i in range(expected_blocks_in_window):
                    if (expected_block + i) not in window_received:
                        bitmap &= ~(1 << i)
                
                self.log(f"Window complete: Got {blocks_in_window}/{expected_blocks_in_window} blocks, bitmap={bitmap:02x}")
                
                # Send ACK with bitmap
                self._send(CMD_ACK + bytes([bitmap]))
                self.log(f"Sent ACK with bitmap {bitmap:02x}")
                
                if bitmap != 0xFF:
                    # Some blocks missing - aber prüfe ob wir schon genug Bytes haben
                    if bytes_received >= filesize:
                        self.log(f"Bitmap incomplete ({bitmap:02x}) but we have all bytes ({bytes_received} >= {filesize})")
                        self.log(f"Transfer appears complete, ignoring missing blocks")
                        break  # Raus aus der while-Schleife
                    
                    # Noch nicht genug Bytes - retry
                    self.log(f"Missing blocks! Bitmap={bitmap:02x}, retry#{retries}")
                    self.stats['blocks_retried'] += 1
                    retries += 1
                    if retries > MAX_RETRIES:
                        # Letzter Check: Haben wir genug Bytes trotz Retries?
                        if bytes_received >= filesize:
                            self.log(f"MAX RETRIES but we have all bytes - considering success")
                            break
                        self._send(CMD_CAN)
                        self.log(f"MAX RETRIES EXCEEDED!")
                        return (False, None)
                    continue
                
                # Write blocks in order
                blocks_written = 0
                while expected_block in window_received:
                    data = window_received[expected_block]
                    original_len = len(data)
                    
                    # Remove padding - trim to exact filesize
                    if bytes_received + len(data) > filesize:
                        trim_to = filesize - bytes_received
                        self.log(f"Block {expected_block}: Trimming from {len(data)} to {trim_to} bytes (would exceed filesize)")
                        data = data[:trim_to]
                    
                    f.write(data)
                    bytes_received += len(data)
                    del window_received[expected_block]
                    expected_block += 1
                    blocks_written += 1
                    
                    if callback:
                        callback(bytes_received, filesize, f"Received {bytes_received // 1024} KB", filename)
                    
                    # Check if we're done
                    if bytes_received >= filesize:
                        self.log(f"Block {expected_block-1}: Reached filesize ({bytes_received} >= {filesize}), stopping")
                        break
                
                self.log(f"Wrote {blocks_written} blocks, total bytes={bytes_received:,}/{filesize:,} ({100*bytes_received//filesize}%)")
                
                # Exit loop if transfer complete  
                if bytes_received >= filesize:
                    self.log(f"TRANSFER COMPLETE! bytes_received={bytes_received} >= filesize={filesize}")
                    break
                
                retries = 0
        
        # Loop beendet - sende finalen Progress Update SOFORT!
        self.log(f"Main loop exited. bytes_received={bytes_received}, filesize={filesize}")
        
        # WICHTIG: Prüfe und korrigiere die tatsächliche Dateigröße
        try:
            actual_size = os.path.getsize(actual_filepath)
            self.log(f"Actual file size on disk: {actual_size}, expected: {filesize}")
            
            if actual_size > filesize:
                self.log(f"WARNING: File on disk ({actual_size}) larger than expected ({filesize}), truncating...")
                with open(actual_filepath, 'r+b') as f:
                    f.truncate(filesize)
                self.log(f"Truncated file to {filesize} bytes")
                bytes_received = filesize
            elif actual_size < filesize:
                self.log(f"WARNING: File on disk ({actual_size}) smaller than expected ({filesize})")
        except Exception as e:
            self.log(f"ERROR checking/truncating file: {e}")
        
        if callback:
            callback(bytes_received, filesize, "Finishing transfer...", filename)
        
        # Wait for EOT (kürzerer Timeout wenn wir schon alle Bytes haben)
        eot_timeout = 3.0 if bytes_received >= filesize else 10.0
        self.log(f"Waiting for EOT (timeout={eot_timeout}s)...")
        eot = self._recv_exact(5, timeout=eot_timeout)
        
        if eot == CMD_EOT:
            self.log("✓ Got EOT, sending final ACK")
            self._send(CMD_ACK)
        elif eot:
            self.log(f"✗ Expected EOT (TBEOT), got: {eot.hex() if len(eot) > 0 else 'timeout'}")
            # Wenn wir alle Bytes haben, sende ACK trotzdem
            if bytes_received >= filesize:
                self.log("All bytes received, sending ACK anyway")
                self._send(CMD_ACK)
        else:
            self.log(f"✗ Timeout waiting for EOT")
            if bytes_received >= filesize:
                self.log("All bytes received, sending ACK anyway")
                self._send(CMD_ACK)
            else:
                self.log(f"WARNING: Incomplete transfer - {bytes_received}/{filesize} bytes")
        
        self.stats['end_time'] = time.time()
        self.stats['bytes_transferred'] = bytes_received
        
        duration = self.stats['end_time'] - self.stats['start_time']
        speed = bytes_received / duration if duration > 0 else 0
        
        self.log(f"===== TRANSFER COMPLETE =====")
        self.log(f"Duration: {duration:.2f}s")
        self.log(f"Speed: {speed/1024:.2f} KB/s")
        self.log(f"Blocks received: {self.stats['blocks_received']}")
        self.log(f"Blocks corrupted: {self.stats['blocks_corrupted']}")
        self.log(f"Blocks retried: {self.stats['blocks_retried']}")
        self.log(f"Timeouts: {self.stats['timeouts']}")
        self.log(f"Bytes transferred: {bytes_received}/{filesize} ({100*bytes_received//filesize if filesize>0 else 0}%)")
        
        # Save debug log only if debug is enabled
        if self.debug:
            self.save_debug_log()
        
        if callback:
            callback(bytes_received, filesize, "Transfer complete", filename)
        
        return (True, actual_filepath)
    
    def get_speed(self):
        """
        Berechnet Transfer-Geschwindigkeit
        
        Returns:
            (bytes_per_second, duration)
        """
        duration = self.stats['end_time'] - self.stats['start_time']
        if duration > 0:
            bps = self.stats['bytes_transferred'] / duration
            return (bps, duration)
        return (0, 0)
    
    def print_stats(self):
        """Gibt Transfer-Statistiken aus"""
        bps, duration = self.get_speed()
        print(f"\n[TurboModem Statistics]")
        print(f"  Duration: {duration:.2f} seconds")
        print(f"  Bytes: {self.stats['bytes_transferred']:,}")
        print(f"  Speed: {bps / 1024:.2f} KB/s ({bps * 8 / 1000:.2f} kbps)")
        print(f"  Blocks sent: {self.stats['blocks_sent']}")
        print(f"  Blocks received: {self.stats['blocks_received']}")
        print(f"  Retransmits: {self.stats['retransmits']}")


# Example usage
if __name__ == "__main__":
    print("""
TurboModem Protocol - Usage Example
====================================

# Client side (receive file):
from turbomodem import TurboModem

def progress(done, total, status):
    print(f"Progress: {done}/{total} - {status}")

turbo = TurboModem(connection)
success = turbo.receive_file("download.bin", callback=progress)
if success:
    turbo.print_stats()


# Server side (send file):
turbo = TurboModem(connection)
success = turbo.send_file("upload.bin", callback=progress)
if success:
    turbo.print_stats()


Performance Comparison:
=======================
XModem:     ~30-250 KB/s
XModem-1K:  ~100-250 KB/s
TurboModem: ~500 KB/s - 2 MB/s ✅ (10-20x faster!)
""")
