// Updated Case 1 Top Module based on case1.list
module top ( MCK, MSI, MSO, MBS, MBC, MBR, MRD, MBO, WEB, CSB, D7, D6 , D5, D4, D3, D2, D1);

    input        MCK;
    input        MSI;
    output       MSO;
    input 	 MBS;
    input        MBC;
    input        MBR;
    output       MRD;
    output       MBO;
    input        WEB, CSB, D7, D6 , D5, D4, D3, D2, D1 ;

    // Input Pad Cell
    PDXOE3DG u_mck ( .PAD(MCK), .XIN(), .XOUT());
    PDUDGZ   u_msi ( .PAD(MSI), .XIN(), .XOUT());
    PDUDGZ   u_mbs ( .PAD(MBS), .XIN(), .XOUT());
    PDUDGZ   u_mbc ( .PAD(MBC), .XIN(), .XOUT());
    PDUDGZ   u_mbr ( .PAD(MBR), .XIN(), .XOUT());
    PDUDGZ   u_web ( .PAD(WEB), .XIN(), .XOUT());
    PDUDGZ   u_csb ( .PAD(CSB), .XIN(), .XOUT());
    PDUDGZ   u_d7  ( .PAD(D7), .XIN(), .XOUT());
    PDUDGZ   u_d7  ( .PAD(D6), .XIN(), .XOUT());
    PDUDGZ   u_d5  ( .PAD(D5), .XIN(), .XOUT());
    PDUDGZ   u_d4  ( .PAD(D4), .XIN(), .XOUT());
    PDUDGZ   u_d3  ( .PAD(D3), .XIN(), .XOUT());
    PDUDGZ   u_d2  ( .PAD(D2), .XIN(), .XOUT());
    PDUDGZ   u_d1  ( .PAD(D1), .XIN(), .XOUT());

    // Output Pad Cell
    PDO08CDG u_mso ( .PAD(MSO), .D(), .E());
    PDO08CDG u_mrd ( .PAD(MRD), .D(), .E());
    PDO08CDG u_mbo ( .PAD(MBO), .D(), .E());

    // Powercut Cell
    PRDIODE u_pc01 ( .PAD(POWERCUT01), .AN());

    // Power/Ground Cells
    PVDD1DG VDDC01 ();
    PVDD2DG VDDIO01 ();
    PVDD2DG VDDIO02 ();
    PVSS3DG VSSCIO01 ();
    PVSS2DG VSSIO01 ();
    PRDIODE POWERCUT01 (); 
    PVDD2DG VDDIO03 ();
    PVSS1DG VSSC01 ();
    PVSS2DG VSSIO02 ();

endmodule
