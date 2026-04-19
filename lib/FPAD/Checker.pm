package FPAD::Checker;

use strict;
use warnings;

sub new {
    my ($class, %args) = @_;
    return bless {
        logger => $args{logger},
        parser => $args{parser},
    }, $class;
}

# --- 執行 Stagger Check ---
sub check_stagger {
    my ($self, $filename) = @_;
    $self->{logger}->info("Running Stagger Check...");
    
    open my $fh, '>', $filename or return;
    print $fh "STAGGER CHECK REPORT\n";
    print $fh "=" x 30 . "\n";

    my $io_count = 0;
    my $max_io_consecutive = 8; # 假設連續 8 根 I/O 就需要一根 P/G

    foreach my $row (@{$self->{parser}->{data}}) {
        my $dir = $row->{DIRECTION};
        
        if ($dir eq 'I' || $dir eq 'O' || $dir eq 'B') {
            $io_count++;
            if ($io_count > $max_io_consecutive) {
                my $msg = "[WARN] Too many consecutive I/Os at Pin $row->{PIN_NUM} ($row->{PIN_NAME})";
                print $fh "$msg\n";
                $self->{logger}->warn($msg);
            }
        } elsif ($dir eq 'P' || $dir eq 'G') {
            $io_count = 0; # 遇到電源或接地，歸零計數
        }
    }

    close $fh;
    $self->{logger}->info("Stagger report generated: $filename");
}

1;
