package FPAD::PDF;

use strict;
use warnings;

sub new {
    my ($class, %args) = @_;
    my $self = {
        logger => $args{logger},
        parser => $args{parser},
    };
    return bless $self, $class;
}

# --- 生成 APR Pin Diagram (zz / DIE_PAD_NUM / 跳過 NC) ---
sub generate_apr_pdf {
    my ($self, $filename) = @_;
    $self->{logger}->info("Generating APR Diagram (Auto-scaling enabled)...");

    eval { require PDF::API2; }; return if $@;
    my $pdf = PDF::API2->new();
    my $page = $pdf->page();
    $page->mediabox(842, 595);

    my $gfx = $page->gfx();
    my $f_bold = $pdf->corefont('Helvetica-Bold');
    my $f_reg  = $pdf->corefont('Helvetica');

    $self->_draw_header($gfx, $page->text(), $f_bold, $f_reg, "APR PIN DIAGRAM");

    # 1. 讀取規格與分組
    my $pkg_str = $self->{parser}->{header}->{PACKAGE} || "64 16 16 16 16";
    my ($type, $l_cnt, $b_cnt, $r_cnt, $t_cnt) = split /\s+/, $pkg_str;
    
    my %data_by_side;
    foreach my $row (@{$self->{parser}->{data}}) {
        my $pname = $row->{PIN_NAME};
        $pname =~ s/^\s+|\s+$//g;
        next if uc($pname) eq 'NC';
        push @{$data_by_side{uc($row->{LOCATION})}}, $row;
    }

    # 2. 計算動態邊長
    my $box_edge = $self->_calc_box_edge($l_cnt, $b_cnt, $r_cnt, $t_cnt, \%data_by_side);
    my ($cx, $cy) = (421, 260);

    $gfx->linewidth(2); $gfx->strokecolor('#000000');
    $gfx->rect($cx - $box_edge/2, $cy - $box_edge/2, $box_edge, $box_edge); $gfx->stroke();

    # 3. 繪圖
    $self->_draw_side_boxes($page, $gfx, $f_reg, 'L', $data_by_side{L}, $cx - $box_edge/2, $cy, $box_edge, $l_cnt, 'APR');
    $self->_draw_side_boxes($page, $gfx, $f_reg, 'B', $data_by_side{B}, $cx, $cy - $box_edge/2, $box_edge, $b_cnt, 'APR');
    $self->_draw_side_boxes($page, $gfx, $f_reg, 'R', $data_by_side{R}, $cx + $box_edge/2, $cy, $box_edge, $r_cnt, 'APR');
    $self->_draw_side_boxes($page, $gfx, $f_reg, 'T', $data_by_side{T}, $cx, $cy + $box_edge/2, $box_edge, $t_cnt, 'APR');

    $pdf->saveas($filename);
}

# --- 生成 Package Pin Diagram (外部視角: xx / PIN_NUM / 保留 NC) ---
sub generate_pkg_pdf {
    my ($self, $filename) = @_;
    $self->{logger}->info("Generating PKG Diagram (Auto-scaling enabled)...");

    eval { require PDF::API2; }; return if $@;
    my $pdf = PDF::API2->new();
    my $page = $pdf->page();
    $page->mediabox(842, 595);

    my $gfx = $page->gfx();
    my $f_bold = $pdf->corefont('Helvetica-Bold');
    my $f_reg  = $pdf->corefont('Helvetica');

    $self->_draw_header($gfx, $page->text(), $f_bold, $f_reg, "PACKAGE PIN DIAGRAM");

    my $pkg_str = $self->{parser}->{header}->{PACKAGE} || "64 16 16 16 16";
    my ($type, $l_cnt, $b_cnt, $r_cnt, $t_cnt) = split /\s+/, $pkg_str;

    # 排重邏輯
    my %pkg_data;
    my @order;
    foreach my $row (@{$self->{parser}->{data}}) {
        my $pnum = $row->{PIN_NUM};
        next if $pnum eq '0' || $pnum eq '-';
        if (!$pkg_data{$pnum}) { $pkg_data{$pnum} = { %$row }; push @order, $pnum; }
    }
    
    my %data_by_side;
    foreach my $pnum (@order) {
        push @{$data_by_side{uc($pkg_data{$pnum}->{LOCATION})}}, $pkg_data{$pnum};
    }

    my $box_edge = $self->_calc_box_edge($l_cnt, $b_cnt, $r_cnt, $t_cnt, \%data_by_side);
    my ($cx, $cy) = (421, 260);

    $gfx->linewidth(2); $gfx->strokecolor('#000000');
    $gfx->rect($cx - $box_edge/2, $cy - $box_edge/2, $box_edge, $box_edge); $gfx->stroke();

    $self->_draw_side_boxes($page, $gfx, $f_reg, 'L', $data_by_side{L}, $cx - $box_edge/2, $cy, $box_edge, $l_cnt, 'PKG');
    $self->_draw_side_boxes($page, $gfx, $f_reg, 'B', $data_by_side{B}, $cx, $cy - $box_edge/2, $box_edge, $b_cnt, 'PKG');
    $self->_draw_side_boxes($page, $gfx, $f_reg, 'R', $data_by_side{R}, $cx + $box_edge/2, $cy, $box_edge, $r_cnt, 'PKG');
    $self->_draw_side_boxes($page, $gfx, $f_reg, 'T', $data_by_side{T}, $cx, $cy + $box_edge/2, $box_edge, $t_cnt, 'PKG');

    $pdf->saveas($filename);
}

# --- 輔助：計算動態邊長 ---
sub _calc_box_edge {
    my ($self, $l, $b, $r, $t, $data) = @_;
    my $max_req = (sort { $b <=> $a } ($l, $b, $r, $t))[0];
    my $max_act = 0;
    foreach my $s ('L','B','R','T') {
        my $cnt = $data->{$s} ? scalar(@{$data->{$s}}) : 0;
        $max_act = $cnt if $cnt > $max_act;
    }
    my $final_max = $max_req > $max_act ? $max_req : $max_act;
    
    my $edge = ($final_max + 1) * 12; # 基礎縮放 12pt/pin
    $edge = 250 if $edge < 250;
    $edge = 480 if $edge > 480; # 最大不超過標頭邊界
    return $edge;
}

# --- 核心繪圖引擎 (含智能縮放) ---
sub _draw_side_boxes {
    my ($self, $page, $gfx, $font, $side, $pins, $bx, $by, $len, $total, $mode) = @_;
    return unless $pins && @$pins;
    
    my $actual_cnt = scalar(@$pins);
    my $calc_total = $actual_cnt > $total ? $actual_cnt : $total;
    my $step = $len / ($calc_total + 1);
    my $idx = 1;

    # 智能縮放盒子大小與字體
    my $box_thickness = $step * 0.8;
    $box_thickness = 6 if $box_thickness > 6; # 最高 6pt
    $box_thickness = 1 if $box_thickness < 1; # 最低 1pt

    my $font_size = $step * 0.9;
    $font_size = 7 if $font_size > 7; # 最高 7pt
    $font_size = 2 if $font_size < 2; # 最低 2pt

    my $box_len = 20; # 引腳長度固定或微調

    foreach my $pin (@$pins) {
        my $pname = $pin->{PIN_NAME};
        my $display_name = $pname;
        if ($pname =~ /%/) {
            my @parts = split(/%/, $pname);
            $display_name = ($mode eq 'APR') ? $parts[-1] : $parts[0];
        }

        # 座標定位
        my ($px, $py, $bw, $bh);
        if ($side eq 'L') { 
            $bw = $box_len; $bh = $box_thickness;
            $px = $bx - $bw; $py = ($by + $len/2) - ($idx * $step) - ($bh/2); 
        } elsif ($side eq 'B') { 
            $bw = $box_thickness; $bh = $box_len;
            $px = ($bx - $len/2) + ($idx * $step) - ($bw/2); $py = $by - $bh; 
        } elsif ($side eq 'R') { 
            $bw = $box_len; $bh = $box_thickness;
            $px = $bx; $py = ($by - $len/2) + ($idx * $step) - ($bh/2); 
        } elsif ($side eq 'T') { 
            $bw = $box_thickness; $bh = $box_len;
            $px = ($bx + $len/2) - ($idx * $step) - ($bw/2); $py = $by; 
        }

        # 繪製盒子與著色
        $gfx->linewidth(0.5); $gfx->strokecolor('#000000');
        my $dir = $pin->{DIRECTION};
        if ($pname =~ /POWERCUT/i) {
            $gfx->fillcolor('#000000'); $gfx->rect($px, $py, $bw, $bh); $gfx->fill();
        } elsif ($dir eq 'P') {
            $gfx->fillcolor('#FF0000'); $gfx->rect($px, $py, $bw, $bh); $gfx->fill();
        } elsif ($dir eq 'G') {
            $gfx->fillcolor('#0000FF'); $gfx->rect($px, $py, $bw, $bh); $gfx->fill();
        } else {
            $gfx->rect($px, $py, $bw, $bh); $gfx->stroke();
        }

        # 數字與標籤標註 (使用動態縮放後的字體)
        my $num = ($mode eq 'APR') ? $pin->{DIE_PAD_NUM} : $pin->{PIN_NUM};
        if ($num ne '-' && ($num == 1 || $num % 5 == 0 || $num eq '0')) {
            my $tn = $page->text(); $tn->font($font, $font_size);
            my ($nx, $ny);
            if ($side eq 'L') { $nx = $bx + 2; $ny = $py; }
            elsif ($side eq 'R') { $nx = $bx - ($font_size*2); $ny = $py; }
            elsif ($side eq 'T') { $nx = $px; $ny = $by - ($font_size*2); }
            elsif ($side eq 'B') { $nx = $px; $ny = $by + 2; }
            $tn->translate($nx, $ny); $tn->text($num);
        }

        my $tl = $page->text(); $tl->font($font, $font_size);
        my ($tx, $ty, $rot) = (0, 0, 0);
        if ($side eq 'L') { $tx = $px - 4; $ty = $py; $rot = 0; }
        elsif ($side eq 'R') { $tx = $px + $bw + 4; $ty = $py; $rot = 0; }
        elsif ($side eq 'T') { $tx = $px + ($bw/2); $ty = $py + $bh + 2; $rot = 90; }
        elsif ($side eq 'B') { $tx = $px + ($bw/2); $ty = $py - 2; $rot = 270; }

        if ($rot != 0) {
            $tl->transform(-translate => [$tx, $ty], -rotate => $rot); $tl->text($display_name);
        } else {
            $tl->translate($tx, $ty);
            $side eq 'L' ? $tl->text_right($display_name) : $tl->text($display_name);
        }
        $idx++;
    }
}

sub _draw_header {
    my ($self, $gfx, $txt, $f_bold, $f_reg, $title) = @_;
    
    # 標頭背景框
    $gfx->linewidth(1); $gfx->strokecolor('#000000');
    $gfx->rect(50, 510, 742, 65); $gfx->stroke();
    
    # 主標題
    $txt->font($f_bold, 18);
    $txt->translate(421, 550); $txt->text_center($title);
    
    # 詳細資訊
    $txt->font($f_reg, 10);
    my $header = $self->{parser}->{header};
    
    # 左側: Project
    $txt->translate(60, 530); 
    $txt->text("Project: " . ($header->{'PRODUCTION NO.'} || $header->{'PRODUCTION NO'} || "N/A"));
    
    # 中間: Package
    $txt->translate(421, 530);
    $txt->text_center("Package: " . ($header->{PACKAGE} || "N/A"));
    
    # 右側: Version
    $txt->translate(782, 530);
    $txt->text_right("Version: " . ($header->{VERSION} || "N/A"));
}

1;
