package FPAD::Logger;

use strict;
use warnings;

sub new {
    my ($class) = @_;
    return bless {}, $class;
}

sub info {
    my ($self, $msg) = @_;
    print "[INFO ] $msg\n";
}

sub warn {
    my ($self, $msg) = @_;
    print "[WARN ] $msg\n";
}

sub error {
    my ($self, $msg) = @_;
    print "[ERROR] $msg\n";
}

sub fatal {
    my ($self, $msg) = @_;
    die "[FATAL] $msg\n";
}

1;
