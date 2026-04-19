# lib/fpad_py/checker.py

class Checker:
    def __init__(self, logger, parser):
        self.logger = logger
        self.parser = parser

    def check_stagger(self, filename):
        self.logger.info("Running Stagger Check...")
        
        try:
            with open(filename, 'w') as f:
                f.write("STAGGER CHECK REPORT\n")
                f.write("=" * 30 + "\n")

                io_count = 0
                max_io_consecutive = 8 # 假設連續 8 根 I/O 就需要一根 P/G

                for row in self.parser.data:
                    direction = row['DIRECTION']
                    
                    if direction in ('I', 'O', 'B'):
                        io_count += 1
                        if io_count > max_io_consecutive:
                            msg = f"[WARN] Too many consecutive I/Os at Pin {row['PIN_NUM']} ({row['PIN_NAME']})"
                            f.write(msg + "\n")
                            self.logger.warn(msg)
                    elif direction in ('P', 'G'):
                        io_count = 0 # 遇到電源或接地，歸零計數

            self.logger.info(f"Stagger report generated: {filename}")
        except Exception as e:
            self.logger.error(f"Failed to write stagger report: {e}")
