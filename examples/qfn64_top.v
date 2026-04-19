module top (
    MCK, MSI, MSO, MBS, MBC, MBR, MRD, MBO, WEB, CSB, D7, D6, D5, D4, D3, D2, D1, D0,
    SIG_B1, SIG_B2, SIG_B3, SIG_B4, R_SIG1, R_SIG2, R_SIG3, R_SIG4, R_SIG5, R_SIG6, R_SIG7, R_SIG8,
    R_SIG9, R_SIG10, R_SIG11, R_SIG12, T_SIG1, T_SIG2, T_SIG3, T_SIG4, T_SIG5, T_SIG6, T_SIG7,
    T_SIG8, T_SIG9, T_SIG10, T_SIG11, T_SIG12, EXTRA_P1, EXTRA_G1,
    VDDC1, VDDIO1, VDDIO2, VSSIO1, VSSIO2, VDDIO3, VSSC1, VSSIO3, VDDIO4, VSSC2, VSSIO4, VDDC2, VSSIO5, VSSC3
);

    input  MCK, MSI, MBS, MBC, MBR, WEB, CSB, D7, D6, D5, D4, D3, D2, D1, D0;
    input  R_SIG1, R_SIG2;
    output MSO, MRD, MBO, R_SIG3, R_SIG4;
    inout  SIG_B1, SIG_B2, SIG_B3, SIG_B4, R_SIG5, R_SIG6, R_SIG7, R_SIG8;
    input  VDDC1, VDDIO1, VDDIO2, VDDIO3, VDDIO4, VDDC2, EXTRA_P1;
    output VSSIO1, VSSIO2, VSSC1, VSSIO3, VSSC2, VSSIO4, VSSIO5, VSSC3, EXTRA_G1;

    // Pad Instances
    PDXOE3DG u_mck (.PAD(MCK), .XIN(), .XOUT());
    PDUDGZ   u_msi (.PAD(MSI), .XIN(), .XOUT());
    PDO08CDG u_mso (.PAD(MSO), .D(), .E());
    PDUDGZ   u_mbs (.PAD(MBS), .XIN(), .XOUT());
    PDUDGZ   u_mbc (.PAD(MBC), .XIN(), .XOUT());
    PDUDGZ   u_mbr (.PAD(MBR), .XIN(), .XOUT());
    PDO08CDG u_mrd (.PAD(MRD), .D(), .E());
    PDO08CDG u_mbo (.PAD(MBO), .D(), .E());
    PDUDGZ   u_web (.PAD(WEB), .XIN(), .XOUT());
    PDUDGZ   u_csb (.PAD(CSB), .XIN(), .XOUT());
    PDUDGZ   u_d7  (.PAD(D7), .XIN(), .XOUT());
    PDUDGZ   u_d6  (.PAD(D6), .XIN(), .XOUT());
    PDUDGZ   u_d5  (.PAD(D5), .XIN(), .XOUT());
    PDUDGZ   u_d4  (.PAD(D4), .XIN(), .XOUT());
    PDUDGZ   u_d3  (.PAD(D3), .XIN(), .XOUT());
    PDUDGZ   u_d2  (.PAD(D2), .XIN(), .XOUT());
    PDUDGZ   u_d1  (.PAD(D1), .XIN(), .XOUT());
    PDUDGZ   u_d0  (.PAD(D0), .XIN(), .XOUT());

    // Power/Ground Instances
    PVDD1DG VDDC1 ();
    PVDD2DG VDDIO1 ();
    PVDD2DG VDDIO2 ();
    PVSS2DG VSSIO1 ();
    PVSS2DG VSSIO2 ();
    PVDD2DG VDDIO3 ();
    PVSS1DG VSSC1 ();
    PVSS2DG VSSIO3 ();
    PVDD2DG VDDIO4 ();
    PVSS1DG VSSC2 ();
    PVSS2DG VSSIO4 ();
    PVDD1DG VDDC2 ();
    PVSS2DG VSSIO5 ();
    PVSS1DG VSSC3 ();

    // POWERCUTs
    PRDIODE POWERCUT01 ();
    PRDIODE POWERCUT02 ();
    PRDIODE POWERCUT03 ();

endmodule
