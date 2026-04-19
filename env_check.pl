#!/usr/bin/perl
use strict;
use warnings;

print "Checking environment for FPAD_ASSIGN...\n";

my @modules = qw(PDF::API2 Getopt::Long File::Basename File::Slurp);
my $missing = 0;

foreach my $mod (@modules) {
    eval "require $mod";
    if ($@) {
        print "[ERROR] Missing module: $mod\n";
        $missing++;
    } else {
        my $ver = $mod->VERSION || "installed";
        printf "[ OK  ] %-15s (%s)\n", $mod, $ver;
    }
}

if ($missing) {
    print "\nPlease install missing modules using CPAN or your package manager.\n";
    print "Example: sudo cpan PDF::API2\n";
    exit 1;
} else {
    print "\nEnvironment is READY! Let's start coding.\n";
    exit 0;
}
