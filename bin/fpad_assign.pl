#!/usr/bin/perl
use strict;
use warnings;
use Getopt::Long;
use File::Basename;

# --- Logger ---
package Logger;
sub new { bless {}, shift }
sub info { print "[INFO ] $_[1]\n" }
sub fatal { print "[FATAL] $_[1]\n"; exit 1 }
sub warn { print "[WARN ] $_[1]\n" }

# --- MiniPDF (Hand-rolled PDF Generator) ---
package MiniPDF;
sub new { bless { content => "", xref => [], objs => 0 }, shift }
sub add_obj {
    my ($self, $data) = @_;
    push @{$self->{xref}}, length($self->{content});
    $self->{objs}++;
    $self->{content} .= "$self->{objs} 0 obj\n$data\nendobj\n";
}
sub generate {
    my ($self, $fn, $title, $proj, $pkg, $ver, $data, $mode) = @_;
    $self->{content} = "%PDF-1.4\n";
    $self->add_obj("<< /Type /Catalog /Pages 2 0 R >>");
    $self->add_obj("<< /Type /Pages /Kids [3 0 R] /Count 1 >>");
    $self->add_obj("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 842 595] /Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>");
    $self->add_obj("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>");
    $self->add_obj("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>");

    my $s = "q\n";
    $s .= "BT /F2 18 Tf 0 g 1 0 0 1 320 550 Tm ($title) Tj ET\n";
    $s .= "BT /F1 10 Tf 0 g 1 0 0 1 60 530 Tm (Project: $proj) Tj ET\nBT /F1 10 Tf 0 g 1 0 0 1 350 530 Tm (Package: $pkg) Tj ET\nBT /F1 10 Tf 0 g 1 0 0 1 680 530 Tm (Version: $ver) Tj ET\n";

    my $cx = 421; my $cy = 240;
    my (%pkg_pts, %apr_pts);

    if ($mode == 2) { # Combined
        $self->draw_layer(\$s, $data, $cx, $cy, 350, \%pkg_pts, 1, 0);
        $s .= "[4 2] 0 d\n";
        $self->draw_layer(\$s, $data, $cx, $cy, 200, \%apr_pts, 0, 1);
        $s .= "[] 0 d\n0.3 w\n";
        foreach my $r (@$data) {
            next if $r->{PIN_NAME} eq 'NC';
            my $p_pt = $pkg_pts{$r->{PIN_NUM}}; my $a_pt = $apr_pts{$r->{DIE_PAD_NUM}};
            if ($p_pt && $a_pt) {
                if ($r->{DIRECTION} eq 'P') { $s .= "1 0 0 RG "; } elsif ($r->{DIRECTION} eq 'G') { $s .= "0 0 1 RG "; } else { $s .= "0.5 G "; }
                $s .= "$p_pt->[0] $p_pt->[1] m $a_pt->[0] $a_pt->[1] l S\n";
            }
        }
    } else {
        $self->draw_layer(\$s, $data, $cx, $cy, 350, \%pkg_pts, $mode, 0);
    }
    $s .= "Q\n";
    $self->add_obj("<< /Length ".length($s)." >>\nstream\n".$s."endstream");
    my $start_xref = length($self->{content});
    $self->{content} .= "xref\n0 ".($self->{objs}+1)."\n0000000000 65535 f \n";
    foreach (@{$self->{xref}}) { $self->{content} .= sprintf("%010d 00000 n \n", $_); }
    $self->{content} .= "trailer << /Size ".($self->{objs}+1)." /Root 1 0 R >>\nstartxref\n$start_xref\n%%EOF\n";
    open my $fh, '>', $fn; binmode $fh; print $fh $self->{content}; close $fh;
}
sub draw_layer {
    my ($self, $sr, $data, $cx, $cy, $edge, $pts, $is_pkg, $label_inside) = @_;
    my %sides; my %seen;
    foreach my $r (@$data) {
        my $pname = uc($r->{PIN_NAME});
        next if !$is_pkg && $pname eq 'NC';
        next if $is_pkg && ($r->{PIN_NUM} =~ /^(0|-)$/ || $pname eq 'NC' || $pname =~ /POWERCUT/ || $seen{$r->{PIN_NUM}});
        push @{$sides{$r->{LOCATION}}}, $r; $seen{$r->{PIN_NUM}} = 1 if $is_pkg;
    }
    $$sr .= sprintf("1 w 0 G %.2f %.2f %.2f %.2f re S\n", $cx-$edge/2, $cy-$edge/2, $edge, $edge);
    foreach my $cur (qw(L B R T)) {
        my $pins = $sides{$cur} or next; my $step = $edge / (@$pins + 1); my $fsz = 5; my $box_l = $is_pkg ? 20 : 12;
        for (my $i=0; $i<@$pins; $i++) {
            my $pin = $pins->[$i]; my ($bx, $by, $bw, $bh, $tx, $ty, $matrix);
            my $name = $pin->{PIN_NAME}; if ($name =~ /%/) { my @p = split('%', $name); $name = !$is_pkg ? $p[-1] : $p[0]; }
            $matrix = "1 0 0 1";
            my ($px, $py);
            if ($cur eq 'L') { $bw=$box_l; $bh=$fsz*0.8; $bx=$cx-$edge/2-($label_inside?0:$bw); $by=($cy+$edge/2)-($i+1)*$step-$bh/2; $tx=$bx-(length($name)*3+4); $ty=$by+($bh/2)-($fsz/2); $pts->{$is_pkg?$pin->{PIN_NUM}:$pin->{DIE_PAD_NUM}}=[$cx-$edge/2, $by+$bh/2]; $px=$bx; $py=$by; }
            elsif ($cur eq 'B') { $bw=$fsz*0.8; $bh=$box_l; $bx=($cx-$edge/2)+($i+1)*$step-$bw/2; $by=$cy-$edge/2-($label_inside?0:$bh); $tx=$bx+($bw/2); $ty=$by-2; $matrix="0 -1 1 0"; $pts->{$is_pkg?$pin->{PIN_NUM}:$pin->{DIE_PAD_NUM}}=[$bx+$bw/2, $cy-$edge/2]; $px=$bx; $py=$by; }
            elsif ($cur eq 'R') { $bw=$box_l; $bh=$fsz*0.8; $bx=$cx+$edge/2-($label_inside?$bw:0); $by=($cy-$edge/2)+($i+1)*$step-$bh/2; $tx=$bx+$bw+4; $ty=$by+($bh/2)-($fsz/2); $pts->{$is_pkg?$pin->{PIN_NUM}:$pin->{DIE_PAD_NUM}}=[$cx+$edge/2, $by+$bh/2]; $px=$bx; $py=$by; }
            else { $bw=$fsz*0.8; $bh=$box_l; $bx=($cx+0.5*$edge)-($i+1)*$step-0.5*$bw; $by=$cy+0.5*$edge-($label_inside?$bh:0); $tx=$bx+0.5*$bw; $ty=$by+$bh+2; $matrix="0 1 -1 0"; $pts->{$is_pkg?$pin->{PIN_NUM}:$pin->{DIE_PAD_NUM}}=[$bx+0.5*$bw, $cy+0.5*$edge]; $px=$bx; $py=$by; }
            if ($pin->{DIRECTION} eq 'P') { $$sr .= "1 0 0 rg "; } elsif ($pin->{DIRECTION} eq 'G') { $$sr .= "0 0 1 rg "; } else { $$sr .= "1 g "; }
            $$sr .= sprintf("%.2f %.2f %.2f %.2f re f 0 G %.2f %.2f %.2f %.2f re S\n", $bx, $by, $bw, $bh, $bx, $by, $bw, $bh);
            $$sr .= "BT /F1 $fsz Tf 0 g $matrix $tx $ty Tm ($name) Tj ET\n";
        }
    }
}

# --- Main Logic ---
package main;
my $logger = Logger->new();
my ($lf, @vfs, $apr, $pkg, $comb, $all, $check, $stagger);
GetOptions("list=s"=>\$lf, "v=s{1,}"=>\@vfs, "apr"=>\$apr, "pkg"=>\$pkg, "combined"=>\$comb, "all"=>\$all, "c"=>\$check, "stagger"=>\$stagger);
$all and ($apr=$pkg=$comb=$check=$stagger=1);
usage() if !$lf;

$logger->info("Perl Standalone Starting...");
my $header = {}; my @data; my (%v_ports, %v_insts, %v_net_to_inst, %v_raw_insts);
open my $fh, '<', $lf or die $!; my $in_t = 0;
while (<$fh>) {
    s/^\s+|\s+$//g; next if /^$/ || /^--/;
    if (/PIN_NUM/) { $in_t = 1; next; }
    if (!$in_t) { if (/(.*?)\s*:\s*(.*)/) { my $k = uc($1); $header->{$k} = $2; } }
    else {
        my @v = split; if (@v >= 5) { 
            push @data, { PIN_NUM=>$v[0], DIE_PAD_NUM=>$v[1], PIN_NAME=>$v[2], IO_CELL_NAME=>$v[3], LOCATION=>$v[4], DIRECTION=>$v[5]||'-', INST_NAME=>'-' }; 
        }
    }
}
# Verilog Parsing (Minimal)
foreach my $v_file (@vfs) {
    if (open my $vfh, '<', $v_file) {
        $logger->info("Parsing Verilog: $v_file");
        local $/; my $content = <$vfh>;
        while ($content =~ /(input|output|inout)\s+(?:\[.*?\]\s+)?(.*?);/gs) {
            my $d = uc(substr($1,0,1)); my @pts = split /,/, $2; foreach (@pts) { s/\s+//g; $v_ports{$_}=$d; }
        }
        while ($content =~ /(\w+)\s+(\w+)\s*\((.*?)\);/gs) {
            my ($cell, $inst, $body) = ($1, $2, $3); $v_raw_insts{$inst} = $cell;
            if ($body =~ /\.PAD\s*\(\s*(.*?)\s*\)/s) { my $net = $1; $net =~ s/\s+//g; $v_insts{$net} = $cell; $v_net_to_inst{$net} = $inst; }
        }
    }
}
# Bridge
foreach my $r (@data) {
    next if $r->{PIN_NAME} eq 'NC'; my $sn = $r->{PIN_NAME}; my $pm = ($r->{DIRECTION} =~ /^[PG]$/ || $sn =~ /%/ || $sn =~ /POWERCUT/i);
    if ($pm) { $sn = (split('%', $sn))[-1] if $sn =~ /%/; $r->{IO_CELL_NAME} = $v_raw_insts{$sn} || 'NOT_FOUND' if $r->{IO_CELL_NAME} eq '-'; $r->{INST_NAME} = $sn; }
    else { $r->{IO_CELL_NAME} = $v_insts{$sn} || 'NOT_FOUND' if $r->{IO_CELL_NAME} eq '-'; $r->{INST_NAME} = $v_net_to_inst{$sn} || $sn; $r->{DIRECTION} = $v_ports{$sn} || 'UNKNOWN' if $r->{DIRECTION} eq '-'; }
}

my $base = $lf; $base =~ s/\.\w+$//;
if ($stagger) {
    $logger->info("Running Stagger Check...");
    open my $sfh, '>', "${base}_stagger.rpt"; my $ioc=0;
    foreach (@data) { if ($_->{DIRECTION} =~ /^[IOB]$/) { if (++$ioc > 8) { print $sfh "[WARN] Consecutive I/O at $_->{PIN_NUM}\n"; } } else { $ioc=0; } }
}
if ($check) {
    open my $nfh, '>', "${base}.new";
    foreach (sort keys %$header) { printf $nfh "%-20s : %s\n", $_, $header->{$_}; }
    print $nfh "\nPIN_NUM  DIE_PAD_NUM  PIN_NAME             IO_CELL_NAME  LOC  DIR\n" . ("-"x80) . "\n";
    foreach (@data) { printf $nfh "%-8s %-12s %-20s %-12s %-4s %-4s\n", $_->{PIN_NUM}, $_->{DIE_PAD_NUM}, $_->{PIN_NAME}, $_->{IO_CELL_NAME}, $_->{LOCATION}, $_->{DIRECTION}; }
    
    $logger->info("Generating Innovus IO Constraint...");
    open my $cfh, '>', "${base}_chip.const";
    print $cfh "# Innovus IO Assignment File\nVersion: 2\n\n";
    my %sm = (L=>'left', B=>'bottom', R=>'right', T=>'top');
    foreach my $c (qw(L B R T)) {
        print $cfh "$sm{$c}:\n";
        foreach my $r (@data) { if ($r->{LOCATION} eq $c && $r->{PIN_NAME} ne 'NC') { print $cfh "    (inst name=\"$r->{INST_NAME}\" offset=0 orientation=R0 place_status=fixed spacing=0)\n"; } }
        print $cfh "\n";
    }
}
my $pdf = MiniPDF->new();
$pdf->generate("${base}_apr.pdf", "APR PIN DIAGRAM", ($header->{'PRODUCTION NO.'}||'N/A'), ($header->{'PACKAGE'}||'N/A'), ($header->{'VERSION'}||'N/A'), \@data, 0) if $apr;
$pdf->generate("${base}_pkg.pdf", "PACKAGE PIN DIAGRAM", ($header->{'PRODUCTION NO.'}||'N/A'), ($header->{'PACKAGE'}||'N/A'), ($header->{'VERSION'}||'N/A'), \@data, 1) if $pkg;
$pdf->generate("${base}_combined.pdf", "COMBINED BONDING DIAGRAM", ($header->{'PRODUCTION NO.'}||'N/A'), ($header->{'PACKAGE'}||'N/A'), ($header->{'VERSION'}||'N/A'), \@data, 2) if $comb;
$logger->info("Execution complete.");

sub usage { print "Usage: $0 -list <file> -v <v_files> [-apr] [-pkg] [-combined] [-c] [-stagger] [-all]\n"; exit 1; }
