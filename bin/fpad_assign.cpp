#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <regex>
#include <unordered_map>
#include <algorithm>
#include <iomanip>
#include <sstream>

using namespace std;

struct PinRow {
    string pin_num, die_pad_num, pin_name, io_cell_name, location, direction, load, slew, sso, inst_name;
};

class MiniPDF {
private:
    string p_content; vector<long> xref; int obj_cnt = 0;
    void add_obj(const string& d) { obj_cnt++; xref.push_back(p_content.length()); p_content += to_string(obj_cnt) + " 0 obj\n" + d + "\nendobj\n"; }
    string escape(string s) { string r; for (char c : s) { if (c == '(' || c == ')' || c == '\\') r += '\\'; r += c; } return r; }
    float tw(string s, float sz) { return (float)s.length() * sz * 0.55f; }
    struct Point { float x, y; };

public:
    void generate(const string& fn, const string& title, const string& proj, const string& pkg, const string& ver, const vector<PinRow>& data, int mode) {
        p_content = "%PDF-1.4\n"; xref.clear(); obj_cnt = 0;
        add_obj("<< /Type /Catalog /Pages 2 0 R >>");
        add_obj("<< /Type /Pages /Kids [3 0 R] /Count 1 >>");
        add_obj("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 842 595] /Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>");
        add_obj("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>");
        add_obj("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>");

        stringstream s; s << fixed << setprecision(2) << "q\n";
        s << "BT /F2 18 Tf 0 g 1 0 0 1 320 550 Tm (" << escape(title) << ") Tj ET\n";
        s << "BT /F1 10 Tf 0 g 1 0 0 1 60 530 Tm (Project: " << escape(proj) << ") Tj ET\n";
        s << "BT /F1 10 Tf 0 g 1 0 0 1 350 530 Tm (Package: " << escape(pkg) << ") Tj ET\n";
        s << "BT /F1 10 Tf 0 g 1 0 0 1 680 530 Tm (Version: " << escape(ver) << ") Tj ET\n";

        float cx = 421.0f, cy = 240.0f;
        unordered_map<string, Point> pkg_pts, apr_pts;
        if (mode == 2) {
            draw_layer(s, data, cx, cy, 350.0f, pkg_pts, true, false);
            s << "[4 2] 0 d\n"; draw_layer(s, data, cx, cy, 200.0f, apr_pts, false, true);
            s << "[] 0 d\n0.3 w\n";
            for (const auto& r : data) {
                if (r.pin_name == "NC") continue;
                if (pkg_pts.count(r.pin_num) && apr_pts.count(r.die_pad_num)) {
                    if (r.direction == "P") s << "1 0 0 RG "; else if (r.direction == "G") s << "0 0 1 RG "; else s << "0.5 G ";
                    s << pkg_pts[r.pin_num].x << " " << pkg_pts[r.pin_num].y << " m " << apr_pts[r.die_pad_num].x << " " << apr_pts[r.die_pad_num].y << " l S\n";
                }
            }
        } else {
            draw_layer(s, data, cx, cy, 350.0f, pkg_pts, mode == 1, false);
        }
        s << "Q\n"; string str_data = s.str(); add_obj("<< /Length " + to_string(str_data.length()) + " >>\nstream\n" + str_data + "endstream");
        long start_xref = (long)p_content.length(); p_content += "xref\n0 " + to_string(obj_cnt + 1) + "\n0000000000 65535 f \n";
        for (long x : xref) { stringstream sx; sx << setfill('0') << setw(10) << x << " 00000 n \n"; p_content += sx.str(); }
        p_content += "trailer << /Size " + to_string(obj_cnt + 1) + " /Root 1 0 R >>\nstartxref\n" + to_string(start_xref) + "\n%%EOF\n";
        ofstream ofs(fn, ios::binary); ofs << p_content; ofs.close();
    }

    void draw_layer(stringstream& s, const vector<PinRow>& data, float cx, float cy, float edge, unordered_map<string, Point>& pts, bool is_pkg, bool label_inside) {
        unordered_map<string, vector<PinRow>> sides; unordered_map<string, bool> seen;
        for (const auto& r : data) {
            string pname = r.pin_name; for(auto& c:pname) c=(char)toupper(c);
            if (!is_pkg && pname == "NC") continue;
            if (is_pkg && (r.pin_num == "0" || r.pin_num == "-" || pname == "NC" || pname.find("POWERCUT") != string::npos || seen.count(r.pin_num))) continue;
            sides[r.location].push_back(r); if (is_pkg) seen[r.pin_num] = true;
        }
        s << "1 w 0 G " << (cx - edge/2.0f) << " " << (cy - edge/2.0f) << " " << edge << " " << edge << " re S\n";
        string s_ord[] = {"L", "B", "R", "T"};
        for (const string& cur : s_ord) {
            auto pins = sides[cur]; if (pins.empty()) continue;
            float step = edge / (float)(pins.size() + 1), fsz = 5.0f, box_l = is_pkg ? 20.0f : 12.0f;
            for (size_t i = 0; i < pins.size(); ++i) {
                const auto& pin = pins[i]; float bx, by, bw, bh, tx, ty; string dname = pin.pin_name;
                if (dname.find('%') != string::npos) dname = !is_pkg ? dname.substr(dname.find_last_of('%') + 1) : dname.substr(0, dname.find_first_of('%'));
                string matrix = "1 0 0 1";
                if (cur == "L") { bw=box_l; bh=fsz*0.8f; bx=cx-edge/2.0f-(label_inside?0:bw); by=(cy+edge/2.0f)-(float)(i+1)*step-bh/2.0f; tx=bx-(label_inside?-bw-2:tw(dname,fsz)+4); ty=by+bh/2.0f-fsz/2.0f; pts[is_pkg?pin.pin_num:pin.die_pad_num]={cx-edge/2.0f, by+bh/2.0f}; }
                else if (cur == "B") { bw=fsz*0.8f; bh=box_l; bx=(cx-edge/2.0f)+(float)(i+1)*step-bw/2.0f; by=cy-edge/2.0f-(label_inside?0:bh); tx=bx+bw/2.0f; ty=by-2; matrix="0 -1 1 0"; pts[is_pkg?pin.pin_num:pin.die_pad_num]={bx+bw/2.0f, cy-edge/2.0f}; }
                else if (cur == "R") { bw=box_l; bh=fsz*0.8f; bx=cx+edge/2.0f-(label_inside?bw:0); by=(cy-edge/2.0f)+(float)(i+1)*step-bh/2.0f; tx=bx+bw+4; ty=by+bh/2.0f-fsz/2.0f; pts[is_pkg?pin.pin_num:pin.die_pad_num]={cx+edge/2.0f, by+bh/2.0f}; }
                else { bw=fsz*0.8f; bh=box_l; bx=(cx+edge/2.0f)-(float)(i+1)*step-bw/2.0f; by=cy+edge/2.0f-(label_inside?bh:0); tx=bx+bw/2.0f; ty=by+bh+2; matrix="0 1 -1 0"; pts[is_pkg?pin.pin_num:pin.die_pad_num]={bx+bw/2.0f, cy+edge/2.0f}; }
                if (pin.direction == "P") s << "1 0 0 rg "; else if (pin.direction == "G") s << "0 0 1 rg "; else s << "1 g ";
                s << bx << " " << by << " " << bw << " " << bh << " re f 0 G " << bx << " " << by << " " << bw << " " << bh << " re S\n";
                s << "BT /F1 " << fsz << " Tf 0 g " << matrix << " " << tx << " " << ty << " Tm (" << escape(dname) << ") Tj ET\n";
            }
        }
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
            l = trim(l); if (l.empty() || l.substr(0,2) == "--") continue;
            if (l.find("PIN_NUM") != string::npos) { in_t = true; continue; }
            if (!in_t) { size_t c = l.find(':'); if (c != string::npos) { string k = trim(l.substr(0,c)); for(auto& ch:k) ch=(char)toupper(ch); header[k] = trim(l.substr(c+1)); } }
            else {
                vector<string> v; stringstream sss(l); string t; while (sss >> t) v.push_back(t);
                if (v.size() >= 5) {
                    PinRow r; r.pin_num=v[0]; r.die_pad_num=v[1]; r.pin_name=v[2]; r.io_cell_name=v[3]; r.location=v[4];
                    r.direction=(v.size()>5)?v[5]:"-"; r.inst_name="-"; data.push_back(r);
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
                string cell = (*i)[1].str(), inst = (*i)[2].str(), body = (*i)[3].str(); v_raw_insts[inst] = cell;
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
};

int main(int argc, char* argv[]) {
    string lf; vector<string> vfs; bool apr=0, pkg=0, comb=0, check=0, stagger=0, all=0;
    for (int i=1; i<argc; ++i) {
        string a = argv[i];
        if (a == "-list") lf = argv[++i]; else if (a == "-v") vfs.push_back(argv[++i]);
        else if (a == "-apr") apr = 1; else if (a == "-pkg") pkg = 1; else if (a == "-combined") comb = 1;
        else if (a == "-c") check = 1; else if (a == "-stagger") stagger = 1; else if (a == "-all") all = 1;
    }
    if (all) apr=pkg=comb=check=stagger=1; if (lf.empty()) return 1;
    FPAD_Assign app; app.parse_list(lf); if (!vfs.empty()) { app.parse_verilog(vfs); app.bridge(); }
    string base = lf.substr(0, lf.find_last_of('.')); string prj = app.header.count("PRODUCTION NO.") ? app.header["PRODUCTION NO."] : "N/A";
    if (stagger) {
        ofstream ofs(base + "_stagger.rpt"); ofs << "STAGGER CHECK REPORT\n" << string(30, '=') << "\n"; int ioc=0;
        for (const auto& r : app.data) { if (r.direction=="I"||r.direction=="O"||r.direction=="B") { if (++ioc > 8) ofs << "[WARN] Consecutive I/O at " << r.pin_num << "\n"; } else ioc=0; }
    }
    if (check) {
        ofstream ofs(base + "_chip.const"); ofs << "# Innovus IO Assignment File\nVersion: 2\n\n";
        string ord[]={"L","B","R","T"}, names[]={"left","bottom","right","top"};
        for (int i=0; i<4; ++i) {
            ofs << names[i] << ":\n";
            for (const auto& r : app.data) if (r.location==ord[i] && r.pin_name!="NC")
                ofs << "    (inst name=\"" << r.inst_name << "\" offset=0 orientation=R0 place_status=fixed spacing=0)\n";
            ofs << "\n";
        }
    }
    MiniPDF pdf;
    if (apr) pdf.generate(base + "_apr.pdf", "APR PIN DIAGRAM", prj, app.header["PACKAGE"], app.header["VERSION"], app.data, 0);
    if (pkg) pdf.generate(base + "_pkg.pdf", "PACKAGE PIN DIAGRAM", prj, app.header["PACKAGE"], app.header["VERSION"], app.data, 1);
    if (comb) pdf.generate(base + "_combined.pdf", "COMBINED BONDING DIAGRAM", prj, app.header["PACKAGE"], app.header["VERSION"], app.data, 2);
    cout << "[INFO ] C++ Standalone complete.\n"; return 0;
}
