import json, os, sys

INP = os.path.join(os.path.dirname(__file__), "..", "data", "inputs", "mtf_context.jsonl")
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "outputs", "sample_llm_output.jsonl")

req_inp_keys = {"sym","t","p","exec_tf","TF","px_z","v_z","vwap_z","bb_pos","atr_n",
                "cvd_s","cvd_lvl","oi_d","liq_n","reg",
                "L_sup","L_res","L_q_bid","L_q_ask","L_dsup","L_dres",
                "basis_bp","fund_bp","px_disp_bp","pos","avg","unrlz","rsk"}

req_out_keys = {"sym","t","p","tf","s","c","o","f","conf",
                "sA","fA","confA","prob_cont","sc_in","sc_out","hold","tp_atr","sl_atr","hedge","reasons"}

def check_jsonl(path, req_keys):
    ok = True
    with open(path, encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line: 
                print(f"[WARN] empty line {i}")
                continue
            try:
                obj = json.loads(line)
            except Exception as e:
                print(f"[ERR] JSON parse fail line {i}: {e}")
                ok = False
                continue
            missing = req_keys - set(obj.keys())
            if missing:
                print(f"[ERR] line {i} missing keys: {missing}")
                ok = False
    return ok

def main():
    ok1 = check_jsonl(INP, req_inp_keys)
    ok2 = check_jsonl(OUT, req_out_keys)
    if ok1 and ok2:
        print("[PASS] Input and output files look valid by required keys.")
    else:
        print("[FAIL] Some files failed validation.")
        sys.exit(1)

if __name__ == '__main__':
    main()