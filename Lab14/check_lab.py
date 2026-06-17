import json
import os

def validate_lab():
    print("Dang kiem tra dinh dang bai nop...")

    required_files = [
        "reports/summary.json",
        "reports/benchmark_results.json",
        "analysis/failure_analysis.md"
    ]

    # 1. Kiểm tra sự tồn tại của tất cả file
    missing = []
    for f in required_files:
        if os.path.exists(f):
            print(f"[OK] Tim thay: {f}")
        else:
            print(f"[MISSING] Thieu file: {f}")
            missing.append(f)

    if missing:
        print(f"\nThieu {len(missing)} file. Hay bo sung truoc khi nop bai.")
        return

    # 2. Kiểm tra nội dung summary.json
    try:
        with open("reports/summary.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"File reports/summary.json khong phai JSON hop le: {e}")
        return

    summary_node = data.get("current", data)
    if "metrics" not in summary_node or "metadata" not in summary_node:
        print("File summary.json thieu truong 'metrics' hoac 'metadata'.")
        return

    metrics = summary_node["metrics"]
    metadata = summary_node["metadata"]

    print("\n--- Thong ke nhanh ---")
    print(f"Tong so cases: {metadata.get('total', 'N/A')}")
    print(f"Diem trung binh: {metrics.get('avg_score', 0):.2f}")

    # EXPERT CHECKS
    has_retrieval = "hit_rate" in metrics
    if has_retrieval:
        print(f"[OK] Da tim thay Retrieval Metrics (Hit Rate: {metrics['hit_rate']*100:.1f}%)")
    else:
        print("CANH BAO: Thieu Retrieval Metrics (hit_rate).")

    has_multi_judge = "agreement_rate" in metrics
    if has_multi_judge:
        print(f"[OK] Da tim thay Multi-Judge Metrics (Agreement Rate: {metrics['agreement_rate']*100:.1f}%)")
    else:
        print("CANH BAO: Thieu Multi-Judge Metrics (agreement_rate).")

    if metadata.get("version"):
        print("[OK] Da tim thay thong tin phien ban Agent (Regression Mode)")

    if "regression" in data and "decision" in data["regression"]:
        print(f"[OK] Regression Gate: {data['regression']['decision']}")

    print("\nBai lab da san sang de cham diem!")

if __name__ == "__main__":
    validate_lab()
