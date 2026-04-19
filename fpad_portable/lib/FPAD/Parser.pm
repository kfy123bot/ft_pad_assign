package FPAD::Parser;

use strict;
use warnings;
use File::Basename;

sub new {
    my ($class, %args) = @_;
    my $self = {
        logger   => $args{logger},
        list_file => $args{list_file},
        v_files   => $args{v_files} || [],
        header   => {},
        data     => [],
        v_ports  => {},
        v_insts  => {},      # Net -> Cell_Type
        v_net_to_inst => {}, # Net -> Instance_Name (關鍵修正！)
        v_raw_insts => {},   # Instance_Name -> Cell_Type
    };
    return bless $self, $class;
}

sub parse_list {
    my ($self) = @_;
    my $file = $self->{list_file};
    $self->{logger}->info("Parsing Pin List: $file");
    open my $fh, '<', $file or $self->{logger}->fatal("Cannot open $file: $!");
    my $in_table = 0;
    while (<$fh>) {
        s/^\s+|\s+$//g; next if /^$/ || /^-+$/;
        if (/^(PRODUCTION NO\.|PKG_TOP_LEFT_PIN|PACKAGE|VERSION)\s*:\s*(.*)/i) {
            $self->{header}->{uc($1)} = $2; next;
        }
        if (/^PIN_NUM\s+DIE_PAD_NUM/) { $in_table = 1; next; }
        if ($in_table) {
            my @cols = split /\s+/, $_;
            if (@cols >= 5) {
                push @{$self->{data}}, {
                    PIN_NUM      => $cols[0],
                    DIE_PAD_NUM  => $cols[1],
                    PIN_NAME     => $cols[2],
                    IO_CELL_NAME => $cols[3],
                    LOCATION     => $cols[4],
                    DIRECTION    => $cols[5] || '-',
                    LOAD         => $cols[6] || '-',
                    SLEW         => $cols[7] || '-',
                    SSO          => $cols[8] || '-',
                    INST_NAME    => '-', # 新增欄位儲存實體名稱
                };
            }
        }
    }
    close $fh;
}

sub parse_verilog {
    my ($self) = @_;
    foreach my $v_file (@{$self->{v_files}}) {
        $self->{logger}->info("Parsing Verilog: $v_file");
        local $/;
        open my $fh, '<', $v_file or next;
        my $content = <$fh>; close $fh;

        while ($content =~ /(input|output|inout)\s+(?:\[.*?\]\s+)?(.*?);/gs) {
            my $dir = uc(substr($1, 0, 1));
            foreach my $p (split /,\s*/, $2) { $p =~ s/^\s+|\s+$//g; $self->{v_ports}->{$p} = $dir; }
        }

        while ($content =~ /(\w+)\s+(\w+)\s*\((.*?)\);/gs) {
            my ($cell, $inst, $body) = ($1, $2, $3);
            $self->{v_raw_insts}->{$inst} = $cell;
            if ($body =~ /\.PAD\s*\(\s*(.*?)\s*\)/s) {
                my $net = $1;
                $self->{v_insts}->{$net} = $cell;
                $self->{v_net_to_inst}->{$net} = $inst; # 建立 Net 到 Instance 的對應
            }
        }
    }
}

sub bridge_data {
    my ($self) = @_;
    $self->{logger}->info("Bridging data and extracting Instance Names...");
    foreach my $row (@{$self->{data}}) {
        my $pin_name = $row->{PIN_NAME};
        next if $pin_name eq 'NC';
        
        my $search_name = $pin_name;
        my $power_mode  = 0;
        if ($row->{DIRECTION} =~ /^[PG]$/ || $pin_name =~ /%/ || $pin_name =~ /POWERCUT/i) {
            $power_mode = 1;
            if ($pin_name =~ /%/) { my @p = split /%/, $pin_name; $search_name = $p[-1]; }
        }

        if ($power_mode) {
            $row->{IO_CELL_NAME} = $self->{v_raw_insts}->{$search_name} || 'NOT_FOUND' if $row->{IO_CELL_NAME} eq '-';
            $row->{INST_NAME} = $search_name; # 電源類的 search_name 本身就是 Instance Name
        } else {
            $row->{IO_CELL_NAME} = $self->{v_insts}->{$search_name} || 'NOT_FOUND' if $row->{IO_CELL_NAME} eq '-';
            $row->{INST_NAME} = $self->{v_net_to_inst}->{$search_name} || $search_name; # 抓取真正的實體名稱
            $row->{DIRECTION} = $self->{v_ports}->{$search_name} || 'UNKNOWN' if $row->{DIRECTION} eq '-';
        }
    }
}

1;
