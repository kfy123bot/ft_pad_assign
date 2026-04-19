#!/usr/bin/perl

use strict;
use warnings;
use Getopt::Long;
use File::Basename;
use FindBin;
use lib "$FindBin::Bin/lib";

use FPAD::Logger;
use FPAD::Parser;
use FPAD::PDF;
use FPAD::Checker;
use FPAD::Writer;

my $logger = FPAD::Logger->new();

# 參數接收變數
my ($list_file, @v_files, $do_apr, $do_pkg, $do_check, $do_stagger, $do_all, $help);

# 接收 CLI 參數
GetOptions(
    "list=s" => \$list_file,
    "v=s{1,}" => \@v_files,
    "apr"    => \$do_apr,
    "pkg"    => \$do_pkg,
    "c"      => \$do_check,
    "stagger"=> \$do_stagger,
    "all"    => \$do_all,
    "help"   => \$help,
) or $logger->fatal("Invalid command line options.");

if ($help || (!$list_file && !@v_files)) {
    usage();
    exit 0;
}

if ($do_all) {
    $do_apr = $do_pkg = $do_check = $do_stagger = 1;
}

$logger->fatal("Missing -list <file>") unless $list_file;
$logger->fatal("Missing -v <files...>") unless @v_files;

$logger->info("Starting FPAD_ASSIGN tool...");

# --- Phase 2: Parser 核心 ---
my $parser = FPAD::Parser->new(
    logger    => $logger,
    list_file => $list_file,
    v_files   => \@v_files
);

$parser->parse_list();
$parser->parse_verilog();

# --- Phase 3: 資料聯集 ---
$parser->bridge_data();

# --- Phase 4: 輸出生成 ---

# 1. 生成補完後的清單
if ($do_check || $do_all) {
    my $new_list = $list_file . ".new";
    $logger->info("Generating completed list: $new_list");
    
    open my $ofh, '>', $new_list or $logger->fatal("Cannot write to $new_list: $!");
    
    # 寫入 Header
    foreach my $k (sort keys %{$parser->{header}}) {
        printf $ofh "%-20s : %s\n", $k, $parser->{header}->{$k};
    }
    print $ofh "\n";
    printf $ofh "%-8s %-12s %-20s %-12s %-8s %-10s %-6s %-6s %-6s\n", 
           "PIN_NUM", "DIE_PAD_NUM", "PIN_NAME", "IO_CELL_NAME", "LOCATION", "DIRECTION", "LOAD", "SLEW", "SSO";
    print $ofh "-" x 100 . "\n";

    foreach my $row (@{$parser->{data}}) {
        printf $ofh "%-8s %-12s %-20s %-12s %-8s %-10s %-6s %-6s %-6s\n",
               $row->{PIN_NUM}, $row->{DIE_PAD_NUM}, $row->{PIN_NAME}, 
               $row->{IO_CELL_NAME}, $row->{LOCATION}, $row->{DIRECTION}, 
               $row->{LOAD}, $row->{SLEW}, $row->{SSO};
    }
    close $ofh;
}

# 2. 生成 PDF
my $pdf_gen = FPAD::PDF->new(logger => $logger, parser => $parser);
if ($do_apr || $do_all) {
    $pdf_gen->generate_apr_pdf($list_file . "_apr.pdf");
}
if ($do_pkg || $do_all) {
    $pdf_gen->generate_pkg_pdf($list_file . "_pkg.pdf");
}

# 3. 執行 Stagger Check
if ($do_stagger || $do_all) {
    my $checker = FPAD::Checker->new(logger => $logger, parser => $parser);
    $checker->check_stagger($list_file . "_stagger.rpt");
}

# 4. 生成 Innovus IO Constraint
if ($do_all || $do_check) {
    my $writer = FPAD::Writer->new(logger => $logger, parser => $parser);
    $writer->generate_innovus_io($list_file . "_chip.const");
}

$logger->info("Execution completed successfully.");

sub usage {
    print << "EOF";
FPAD_ASSIGN Tool - Pin Sequence Completion & Visualization

Usage:
    $0 -list <pin.list> -v <netlist.v> [Options]

Required:
    -list <file>    Specify the Pin Sequence 9-column list file.
    -v <files...>   Specify one or more Verilog Netlist files.

Options:
    -apr            Generate APR Pin Diagram (PDF).
    -pkg            Generate Package Pin Diagram (PDF).
    -c              Check consistency and generate .list.new.
    -stagger        Check I/O power/ground stagger density.
    -all            Run all functions above.
    -help           Show this help message.
EOF
}
