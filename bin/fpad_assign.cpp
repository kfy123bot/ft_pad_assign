#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <regex>
#include <unordered_map>
#include <algorithm>
#include <iomanip>
#include <sstream>
#include <cmath>

using namespace std;

struct PinRow {
    string pin_num, die_pad_num, pin_name, io_cell_name, location, direction, load, slew, sso, inst_name;
};

class MiniPDF {
private:
    string p_content; vector<long> xref; int obj_cnt = 0;
    void add_obj(const string& d) { obj_cnt++; xref.push_back(p_content.length()); p_content += to_string(obj_cnt) + " 0 obj\n" + d + "\nendobj\n"; }
    string escape(string s) { string r; for (char c : s) { if (c == '(' || c == ')' || c == '\\') r += '\\'; r += c; } return r; }
    float tw(string s, float sz) { return s.length() * sz * 0.60f; }

public:
    void generate(const string& fn, const string& title, const string& proj, const string& pkg, const string& ver, const vector<PinRow>& raw_data, bool is_apr) {
        p_content = "%PDF-1.4\n"; xref.clear(); obj_cnt = 0;
        add_obj("<< /Type /Catalog /Pages 2 0 R >>");
        add_obj("<< /Type /Pages /Kids [3 0 R] /Count 1 >>");
        add_obj("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 842 595] /Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>");
        add_obj("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>");
        add_obj("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>");

        unordered_map<string, vector<PinRow>> sides;
        unordered_map<string, bool> seen;
        for (const auto& r : raw_data) {
            if (is_apr && r.pin_name == "NC") continue;
            if (!is_apr && (r.pin_num == "0" || r.pin_num == "-" || seen.count(r.pin_num))) continue;
            sides[r.location].push_back(r);
            if (!is_apr) seen[r.pin_num] = true;
        }

        stringstream s; s << fixed << setprecision(3) << "q\n";
        s << "BT /F2 18 Tf 0 g 1 0 0 1 350 550 Tm (" << escape(title) << ") Tj ET\n";
        s << "BT /F1 10 Tf 0 g 1 0 0 1 60 530 Tm (Project: " << escape(proj) << ") Tj ET\n";
        s << "BT /F1 10 Tf 0 g 1 0 0 1 350 530 Tm (Package: " << escape(pkg) << ") Tj ET\n";
        s << "BT /F1 10 Tf 0 g 1 0 0 1 680 530 Tm (Version: " << escape(ver) << ") Tj ET\n";

        float cx = 421.0f, cy = 260.5f, edge = 350.0f;
        s << "2 w 0 G " << (cx - edge/2) << " " << (cy - edge/2) << " " << edge << " " << edge << " re S\n";

        string s_ord[] = {"L", "B", "R", "T"};
        for (const string& cur : s_ord) {
            if (!sides.count(cur)) continue;
            auto pins = sides[cur]; float step = edge / (pins.size() + 1);
            float fsz = 6.0f, p_box = 15.0f;
            for (size_t i = 0; i < pins.size(); ++i) {
                const auto& pin = pins[i]; float bx, by, bw, bh, tx, ty;
                string dname = pin.pin_name; if (dname.find('%') != string::npos) dname = is_apr ? dname.substr(dname.find_last_of('%') + 1) : dname.substr(0, dname.find_first_of('%'));

                string matrix = "1 0 0 1"; 
                if (cur == "L") { bw=p_box; bh=fsz*0.8; bx=cx-edge/2-bw; by=(cy+edge/2)-(i+1)*step-bh/2; tx=bx-tw(dname,fsz)-5; ty=by; }
                else if (cur == "B") { bw=fsz*0.8; bh=p_box; bx=(cx-edge/2)+(i+1)*step-bw/2; by=cy-edge/2-bh; tx=bx; ty=by-10; matrix="0 -1 1 0"; }
                else if (cur == "R") { bw=p_box; bh=fsz*0.8; bx=cx+edge/2; by=(cy-edge/2)+(i+1)*step-bh/2; tx=bx+bw+5; ty=by; }
                else { bw=fsz*0.8; bh=p_box; bx=(cx+edge/2)-(i+1)*step-bw/2; by=cy+edge/2; tx=bx; ty=by+bh+5; matrix="0 1 -1 0"; }

                if (pin.direction == "P") s << "1 0 0 rg\n"; else if (pin.direction == "G") s << "0 0 1 rg\n"; else s << "0.9 g\n";
                s << bx << " " << by << " " << bw << " " << bh << " re f\n0 G " << bx << " " << by << " " << bw << " " << bh << " re S\n";
                s << "BT /F1 " << fsz << " Tf 0 g " << matrix << " " << tx << " " << ty << " Tm (" << escape(dname) << ") Tj ET\n";
                
                string lbl = is_apr ? pin.die_pad_num : pin.pin_num;
                if (lbl != "-" && (lbl == "1" || (isdigit(lbl[0]) && stoi(lbl) % 5 == 0))) {
                    float lx, ly; if (cur=="L") {lx=bx+bw+2; ly=by;} else if (cur=="R") {lx=bx-tw(lbl,fsz)-2; ly=by;}
                    else if (cur=="T") {lx=bx; ly=cy+edge/2-10;} else {lx=bx; ly=cy-edge/2+2;}
                    s << "BT /F2 " << fsz << " Tf 0 g 1 0 0 1 " << lx << " " << ly << " Tm (" << lbl << ") Tj ET\n";
                }
            }
        }
        s << "Q\n"; string str_data = s.str(); add_obj("<< /Length " + to_string(str_data.length()) + " >>\nstream\n" + str_data + "endstream");
        long start_xref = p_content.length(); p_content += "xref\n0 " + to_string(obj_cnt + 1) + "\n0000000000 65535 f \n";
        for (long x : xref) { stringstream sx; sx << setfill('0') << setw(10) << x << " 00000 n \n"; p_content += sx.str(); }
        p_content += "trailer << /Size " + to_string(obj_cnt + 1) + " /Root 1 0 R >>\nstartxref\n" + to_string(start_xref) + "\n%%EOF\n";
        ofstream ofs(fn, ios::binary); ofs << p_content; ofs.close();
    }
};

class FPAD_Assign {
public:
    unordered_map<string, string> header; vector<PinRow> data;
    unordered_map<string, string> v_ports, v_insts, v_net_to_inst, v_raw_insts;
    string trim(string s) { s.erase(0, s.find_first_not_of(" \t\r\n")); s.erase(s.find_last_not_of(" \t\r\n")+1); return s; }
    void parse_list(const string& fn) {
        ifstream ifs(fn); string l; bool in_t = false;
        while (getline(ifs, l)) {
            l = trim(l); if (l.empty() || l[0] == '-') continue;
            if (l.find("PIN_NUM") != string::npos) { in_t = true; continue; }
            if (!in_t) { size_t c = l.find(':'); if (c != string::npos) { string k = trim(l.substr(0,c)); for(auto& ch:k) ch=toupper(ch); header[k] = trim(l.substr(c+1)); } }
            else {
                vector<string> v; stringstream sss(l); string t; while (sss >> t) v.push_back(t);
                if (v.size() >= 5) {
                    PinRow r; r.pin_num=v[0]; r.die_pad_num=v[1]; r.pin_name=v[2]; r.io_cell_name=v[3]; r.location=v[4];
                    r.direction=(v.size()>5)?v[5]:"-"; r.load=(v.size()>6)?v[6]:"-"; r.slew=(v.size()>7)?v[7]:"-"; r.sso=(v.size()>8)?v[8]:"-"; r.inst_name="-";
                    data.push_back(r);
                }
            }
        }
    }
    void parse_verilog(const vector<string>& vfs) {
        for (const auto& f : vfs) {
            ifstream ifs(f); if (!ifs.is_open()) continue;
            stringstream buf; buf << ifs.rdbuf(); string content = buf.str();
            regex p_re("(input|output|inout)\\s+(?:\\[.*?\\]\\s+)?(.*?);");
            for (auto i = sregex_iterator(content.begin(), content.end(), p_re); i != sregex_iterator(); ++i) {
                string d = (*i)[1].str().substr(0,1); transform(d.begin(), d.end(), d.begin(), ::toupper);
                string names = (*i)[2].str(); regex n_re("(\\w+)");
                for (auto j = sregex_iterator(names.begin(), names.end(), n_re); j != sregex_iterator(); ++j) v_ports[(*j).str()] = d;
            }
            regex inst_re("(\\w+)\\s+(\\w+)\\s*\\((.*?)\\);");
            for (auto i = sregex_iterator(content.begin(), content.end(), inst_re); i != sregex_iterator(); ++i) {
                string cell = (*i)[1].str(), inst = (*i)[2].str(), body = (*i)[3].str();
                v_raw_insts[inst] = cell;
                regex pad_re("\\.PAD\\s*\\(\\s*(.*?)\\s*\\)"); smatch m;
                if (regex_search(body, m, pad_re)) { string net = m[1].str(); v_insts[net] = cell; v_net_to_inst[net] = inst; }
            }
        }
    }
    void bridge() {
        for (auto& r : data) {
            if (r.pin_name == "NC") continue; string sn = r.pin_name;
            bool pwr = (r.direction == "P" || r.direction == "G" || sn.find('%') != string::npos || sn.find("POWERCUT") != string::npos || sn.find("powercut") != string::npos);
            if (pwr) { if (sn.find('%') != string::npos) sn = sn.substr(sn.find_last_of('%') + 1); if (r.io_cell_name == "-") r.io_cell_name = v_raw_insts.count(sn) ? v_raw_insts[sn] : "NOT_FOUND"; r.inst_name = sn; }
            else { if (r.io_cell_name == "-") r.io_cell_name = v_insts.count(sn) ? v_insts[sn] : "NOT_FOUND"; r.inst_name = v_net_to_inst.count(sn) ? v_net_to_inst[sn] : sn; if (r.direction == "-") r.direction = v_ports.count(sn) ? v_ports[sn] : "UNKNOWN"; }
        }
    }
    void check_stagger(const string& fn) {
        ofstream ofs(fn); ofs << "STAGGER CHECK REPORT\n" << string(30, '=') << "\n"; int io_count = 0;
        for (const auto& r : data) {
            if (r.direction == "I" || r.direction == "O" || r.direction == "B") { if (++io_count > 8) ofs << "[WARN] Too many consecutive I/Os at Pin " << r.pin_num << " (" << r.pin_name << ")\n"; }
            else if (r.direction == "P" || r.direction == "G") io_count = 0;
        }
    }
    void generate_new_list(const string& fn) {
        ofstream ofs(fn); for (auto const& [k, v] : header) ofs << left << setw(20) << k << " : " << v << "\n";
        ofs << "\n" << left << setw(10) << "PIN_NUM" << " " << setw(12) << "DIE_PAD_NUM" << " " << setw(15) << "PIN_NAME" << " " << setw(20) << "IO_CELL_NAME" << " " << setw(10) << "LOCATION" << " " << setw(5) << "DIR" << "\n";
        ofs << string(80, '-') << "\n"; for (const auto& r : data) ofs << left << setw(10) << r.pin_num << " " << setw(12) << r.die_pad_num << " " << setw(15) << r.pin_name << " " << setw(20) << r.io_cell_name << " " << setw(10) << r.location << " " << setw(5) << r.direction << "\n";
    }
    void generate_innovus(const string& fn) {
        ofstream ofs(fn); ofs << "# Innovus IO Assignment File (C++)\nVersion: 2\n\n";
        unordered_map<string, vector<string>> sides; for (const auto& r : data) if (r.pin_name != "NC") sides[r.location].push_back(r.inst_name);
        string ord[] = {"L", "B", "R", "T"}, names[] = {"left", "bottom", "right", "top"};
        for (int i=0; i<4; ++i) { ofs << names[i] << ":\n"; for (const auto& inst : sides[ord[i]]) ofs << "    (inst name=\"" << inst << "\" spacing=0 offset=0 place_status=placed)\n"; ofs << "\n"; }
    }
};

int main(int argc, char* argv[]) {
    string lf; vector<string> vfs; bool apr=0, pkg=0, check=0, stagger=0, all=0;
    for (int i=1; i<argc; ++i) {
        string a = argv[i];
        if (a == "-list") lf = argv[++i]; else if (a == "-v") vfs.push_back(argv[++i]);
        else if (a == "-apr") apr = 1; else if (a == "-pkg") pkg = 1; else if (a == "-c") check = 1;
        else if (a == "-stagger") stagger = 1; else if (a == "-all") all = 1;
    }
    if (lf.empty() || vfs.empty()) { cout << "Usage: " << argv[0] << " -list <file> -v <v_files> [-apr] [-pkg] [-c] [-stagger] [-all]\n"; return 1; }
    if (all) apr=pkg=check=stagger=1;
    FPAD_Assign app; app.parse_list(lf); app.parse_verilog(vfs); app.bridge();
    string base = lf.substr(0, lf.find_last_of('.'));
    if (stagger) app.check_stagger(base + "_stagger.rpt");
    if (check) { app.generate_new_list(base + ".new"); app.generate_innovus(base + "_chip.const"); }
    if (apr || pkg) {
        MiniPDF pdf; string prj = app.header.count("PRODUCTION NO.") ? app.header["PRODUCTION NO."] : "N/A";
        if (apr) pdf.generate(base + "_apr.pdf", "APR PIN DIAGRAM", prj, app.header["PACKAGE"], app.header["VERSION"], app.data, true);
        if (pkg) pdf.generate(base + "_pkg.pdf", "PACKAGE PIN DIAGRAM", prj, app.header["PACKAGE"], app.header["VERSION"], app.data, false);
    }
    cout << "[INFO ] FPAD_ASSIGN (C++) completed successfully.\n";
    return 0;
}
