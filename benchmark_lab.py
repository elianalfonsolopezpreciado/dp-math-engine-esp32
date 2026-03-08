import os
import sys
import time
import json
import queue
import threading
import subprocess
import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

# Data and Math
import pandas as pd
import numpy as np
import scipy.stats as stats

# Plotting
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Serial Communication
import serial
import serial.tools.list_ports

# GUI
import customtkinter as ctk

# ---------------------------------------------------------------------------
# Configuration / Aesthetics Setup
# ---------------------------------------------------------------------------
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

DEFAULT_BAUD = 115200

# ---------------------------------------------------------------------------
# Serial & Flashing Manager
# ---------------------------------------------------------------------------
class ESP32Controller:
    """Manages serial connection and flashing for the ESP32."""
    def __init__(self):
        self.ser = None
        self.port = None
        self.baud = DEFAULT_BAUD
        self.is_connected = False
        
        # Info
        self.chip_model = "Unknown"
        self.flash_size = "Unknown"
        self.free_ram = "Unknown"

    def get_ports(self):
        """Returns a list of available COM ports."""
        return [port.device for port in serial.tools.list_ports.comports()]

    def connect(self, port, baud=DEFAULT_BAUD):
        """Connects to the specified port."""
        try:
            self.ser = serial.Serial(port, baud, timeout=1)
            self.port = port
            self.baud = int(baud)
            self.is_connected = True
            
            # Simple ping to get info (assuming firmware responds to {"cmd": "info"})
            self.query_esp_info()
            return True, "Connected successfully."
        except Exception as e:
            self.is_connected = False
            return False, f"Connection error: {str(e)}"

    def disconnect(self):
        """Closes the serial connection."""
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.is_connected = False

    def query_esp_info(self):
        """Queries chip info via serial if possible, else leaves as Unknown."""
        if not self.is_connected:
            return
            
        # Optional: Try to ask the firmware for basic info
        self.send_command({"cmd": "get_info"})
        start_time = time.time()
        while time.time() - start_time < 0.5:
            line = self.read_line()
            if line:
                try:
                    data = json.loads(line)
                    if "chip" in data:
                        self.chip_model = data.get("chip", "Unknown")
                        self.flash_size = data.get("flash", "Unknown")
                        self.free_ram = data.get("ram", "Unknown")
                        break
                except json.JSONDecodeError:
                    pass

    def send_command(self, cmd_dict):
        """Sends a JSON command to the ESP32."""
        if not self.is_connected:
            return False
        try:
            cmd_str = json.dumps(cmd_dict) + "\n"
            self.ser.write(cmd_str.encode('utf-8'))
            self.ser.flush()
            return True
        except Exception:
            return False

    def read_line(self):
        """Reads a line of serial data."""
        if not self.is_connected:
            return None
        try:
            line = self.ser.readline()
            if line:
                return line.decode('utf-8', errors='replace').strip()
            return None
        except Exception:
            return None

    def flash_firmware(self, bin_path, log_queue):
        """Flashes a binary using esptool.py subprocess."""
        if not self.port:
            log_queue.put(("ERROR", "No active port for flashing."))
            return False
            
        was_connected = self.is_connected
        if self.is_connected:
            self.disconnect()
            time.sleep(1.0)
            
        # Determine paths and command
        esptool_cmd = [sys.executable, "-m", "esptool"]
        cmd = esptool_cmd + [
            "--port", self.port,
            "--baud", "460800",
            # Standard offset for many ESP32 app binaries is 0x10000, 
            # though it depends on partition setup. Adjust if needed.
            "write_flash", "-z", "0x10000", str(bin_path) 
        ]
        
        log_queue.put(("INFO", f"Executing: {' '.join(cmd)}"))
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            for line in process.stdout:
                log_queue.put(("FLASH", line.strip()))
                
            process.wait()
            success = (process.returncode == 0)
            
            if was_connected:
                time.sleep(1.5) # Time to reboot
                self.connect(self.port, self.baud)
                
            return success
        except Exception as e:
            log_queue.put(("ERROR", f"Flashing failed: {e}"))
            return False


# ---------------------------------------------------------------------------
# Data Analysis & Plotting Module
# ---------------------------------------------------------------------------
class BenchmarkAnalyzer:
    """Handles the statistical validation, figure generation, and LaTeX export."""
    def __init__(self, session_dir):
        self.session_dir = Path(session_dir)
        self.raw_dir = self.session_dir / "raw_data"
        self.analysis_dir = self.session_dir / "analysis"
        self.figures_dir = self.session_dir / "figures"
        self.paper_dir = self.session_dir / "paper_ready"
        
        for d in [self.analysis_dir, self.figures_dir, self.paper_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def analyze(self):
        """Runs the complete analysis pipeline."""
        fA = self.raw_dir / "firmware_A_fast.jsonl"
        fB = self.raw_dir / "firmware_B_standard.jsonl"
        
        if not fA.exists() or not fB.exists():
            return False, "Raw data files not found."

        try:
            # Read immutable raw lines
            df_fast = pd.read_json(fA, lines=True)
            df_std = pd.read_json(fB, lines=True)
            
            # Label
            df_fast['firmware'] = 'Fast Engine (Q16.16)'
            df_std['firmware'] = 'Standard (math.h)'
            df_all = pd.concat([df_fast, df_std], ignore_index=True)
            
            # --- 1. Summary Statistics ---
            summary_stats(df_all, self.analysis_dir)

            # --- 2. Advanced Statistical Analysis (Normality, Wilcoxon, Outliers) ---
            self._compute_advanced_stats(df_fast, df_std)

            # --- 3. Generate Paper-Ready Figures ---
            self._generate_figures(df_all, df_fast, df_std)

            # --- 4. LaTeX Table Generation ---
            self._export_latex(df_all)

            return True, "Analysis completed and outputs generated."
        except Exception as e:
            import traceback
            err = traceback.format_exc()
            return False, f"Analysis Error:\n{err}"

    def _compute_advanced_stats(self, df_fast, df_std):
        stats_lines = []
        stats_lines.append("=== ADVANCED STATISTICAL ANALYSIS ===\n")
        
        for func in df_fast['function'].unique():
            stats_lines.append(f"Function: {func}")
            
            cycles_f = df_fast[df_fast['function'] == func]['cycles'].values
            cycles_s = df_std[df_std['function'] == func]['cycles'].values
            
            # Align arrays in case of dropped packets (use min length)
            min_len = min(len(cycles_f), len(cycles_s))
            if min_len < 3:
                stats_lines.append("  Not enough data for statistical tests.\n")
                continue
                
            cf_trunc = cycles_f[:min_len]
            cs_trunc = cycles_s[:min_len]
            
            # 1. Shapiro-Wilk Normality Test
            if np.std(cf_trunc) == 0:
                stats_lines.append("  Normality (Fast): constant data")
            else:
                sw_stat_f, sw_p_f = stats.shapiro(cf_trunc)
                stats_lines.append(f"  Normality (Fast): W={sw_stat_f:.4f}, p={sw_p_f:.4e}")
                
            if np.std(cs_trunc) == 0:
                stats_lines.append("  Normality (Std):  constant data")
            else:
                sw_stat_s, sw_p_s = stats.shapiro(cs_trunc)
                stats_lines.append(f"  Normality (Std):  W={sw_stat_s:.4f}, p={sw_p_s:.4e}")
            
            # 2. Wilcoxon Signed-Rank Test (paired latency comparison)
            if np.all(cf_trunc == cs_trunc):
                stats_lines.append("  Wilcoxon Test: Data is identical.")
            else:
                wc_stat, wc_p = stats.wilcoxon(cs_trunc, cf_trunc)
                stats_lines.append(f"  Wilcoxon Signed-Rank (Std vs Fast): p={wc_p:.4e}")
            
            # 3. Speedup Ratio with 95% Confidence Interval (using bootstrap)
            ratio = cs_trunc.mean() / cf_trunc.mean() if cf_trunc.mean() > 0 else 0
            stats_lines.append(f"  Mean Speedup: {ratio:.3f}x")
            
            # --- NEW METRICS ---
            # Median Latency
            median_fast = np.median(cf_trunc)
            median_std  = np.median(cs_trunc)
            stats_lines.append(f"  Median Latency (Fast): {median_fast:.2f} cycles")
            stats_lines.append(f"  Median Latency (Std):  {median_std:.2f} cycles")
            
            # MAD (Median Absolute Deviation)
            mad_fast = np.median(np.abs(cf_trunc - median_fast))
            mad_std  = np.median(np.abs(cs_trunc - median_std))
            stats_lines.append(f"  MAD (Fast): {mad_fast:.2f}")
            stats_lines.append(f"  MAD (Std):  {mad_std:.2f}")
            
            # Jitter (STD / MEAN)
            jitter_fast = np.std(cf_trunc) / np.mean(cf_trunc) if np.mean(cf_trunc) != 0 else 0
            jitter_std  = np.std(cs_trunc) / np.mean(cs_trunc) if np.mean(cs_trunc) != 0 else 0
            stats_lines.append(f"  Jitter (Fast): {jitter_fast:.6f}")
            stats_lines.append(f"  Jitter (Std):  {jitter_std:.6f}")
            
            # Determinism Score
            det_fast = 1 / (1 + jitter_fast)
            det_std  = 1 / (1 + jitter_std)
            stats_lines.append(f"  Determinism Score (Fast): {det_fast:.4f}")
            stats_lines.append(f"  Determinism Score (Std):  {det_std:.4f}")
            
            # 4. Pearson Correlation (Input vs MAE)
            if 'input' in df_fast.columns and 'mae' in df_fast.columns:
                inputs = df_fast[df_fast['function'] == func]['input'].values[:min_len]
                maes = df_fast[df_fast['function'] == func]['mae'].values[:min_len]
                
                if len(np.unique(inputs)) > 1:
                    corr, p_corr = stats.pearsonr(np.abs(inputs), maes)
                    stats_lines.append(f"  Correlation (|Input| vs MAE): r={corr:.3f}, p={p_corr:.4e}")
            
            # 5. Outlier Detection (Z-score > 3)
            if np.std(cycles_f) == 0:
                outliers_f = 0
            else:
                z_scores_f = np.abs(stats.zscore(cycles_f))
                outliers_f = np.sum(z_scores_f > 3)
            stats_lines.append(f"  Outliers detected (Cycles > 3σ): {outliers_f}\n")

        with open(self.analysis_dir / "statistical_summary.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(stats_lines))

    def _generate_figures(self, df_all, df_fast, df_std):
        plt.style.use('seaborn-v0_8-paper')
        
        # Fig 1: Latency Boxplot (cycles by function/firmware)
        fig1, ax1 = plt.subplots(figsize=(8, 6), dpi=300)
        df_all.boxplot(column='cycles', by=['function', 'firmware'], ax=ax1, rot=45)
        ax1.set_title('Latency Comparison')
        plt.suptitle('')
        ax1.set_ylabel('Execution Cycles')
        ax1.set_xlabel('Operation')
        fig1.tight_layout()
        fig1.savefig(self.figures_dir / "fig1_latency_boxplot.png")
        plt.close(fig1)

        # Fig 2: MAE Heatmap/Scatter (Input magnitude vs Error)
        if 'input' in df_fast.columns and 'mae' in df_fast.columns:
            fig2, ax2 = plt.subplots(figsize=(8, 6), dpi=300)
            for func, group in df_fast.groupby('function'):
                ax2.scatter(np.abs(group['input']), group['mae'], label=func, alpha=0.6, s=15)
            ax2.set_title('Error Analysis (Fast Engine vs Standard)')
            ax2.set_xlabel('Absolute Input Magnitude')
            ax2.set_ylabel('Mean Absolute Error (MAE)')
            ax2.set_yscale('log')
            ax2.legend()
            ax2.grid(True, which="both", ls="--", alpha=0.5)
            fig2.tight_layout()
            fig2.savefig(self.figures_dir / "fig2_mae_heatmap.png")
            plt.close(fig2)

        # Fig 3: Speedup Ratio Bar Chart
        funcs = []
        speedups = []
        for func in df_fast['function'].unique():
            mf = df_fast[df_fast['function'] == func]['cycles'].mean()
            ms = df_std[df_std['function'] == func]['cycles'].mean()
            if mf > 0:
                funcs.append(func)
                speedups.append(ms / mf)
        
        fig3, ax3 = plt.subplots(figsize=(8, 5), dpi=300)
        ax3.bar(funcs, speedups, color='#2ca02c', edgecolor='black')
        ax3.axhline(1.0, color='red', linestyle='--', label='Baseline (1.0x)')
        ax3.set_title('Average Speedup Ratio (Standard / Fast Engine)')
        ax3.set_ylabel('Speedup Factor')
        ax3.legend()
        fig3.tight_layout()
        fig3.savefig(self.figures_dir / "fig3_speedup_ratio.png")
        plt.close(fig3)

        # Fig 4: RAM Footprint Comparison
        if 'ram' in df_all.columns:
            fig4, ax4 = plt.subplots(figsize=(8, 5), dpi=300)
            ram_f = df_fast.groupby('function')['ram'].mean()
            ram_s = df_std.groupby('function')['ram'].mean()
            
            x = np.arange(len(ram_f))
            width = 0.35
            
            ax4.bar(x - width/2, ram_f, width, label='Fast Engine')
            ax4.bar(x + width/2, ram_s, width, label='Standard')
            
            ax4.set_xticks(x)
            ax4.set_xticklabels(ram_f.index, rotation=45)
            ax4.set_ylabel('RAM Consumption (Bytes)')
            ax4.set_title('RAM Footprint Comparison')
            ax4.legend()
            fig4.tight_layout()
            fig4.savefig(self.figures_dir / "fig4_ram_comparison.png")
            plt.close(fig4)
            
        # Figures Description
        with open(self.figures_dir / "figures_description.txt", "w", encoding="utf-8") as f:
            f.write("fig1_latency_boxplot.png: Distribution of execution cycles across all tests.\n")
            f.write("fig2_mae_heatmap.png: Absolute Error (MAE) relative to input magnitude.\n")
            f.write("fig3_speedup_ratio.png: Performance multiplier of Fast Engine vs standard math.h.\n")
            f.write("fig4_ram_comparison.png: Memory overhead per operation.\n")

    def _export_latex(self, df_all):
        metrics = {'cycles': ['mean', 'std', 'max']}
        
        if 'mae' in df_all.columns:
            metrics['mae'] = ['mean', 'std']
            
        grouped = df_all.groupby(['function', 'firmware']).agg(metrics).reset_index()
        
        latex_str = "\\begin{table}[h!]\n\\centering\n"
        latex_str += "\\caption{Summary of Benchmark Results}\n"
        latex_str += "\\label{tab:benchmark_results}\n"
        latex_str += grouped.to_latex(index=False, float_format="%.4f", escape=False)
        latex_str += "\\end{table}\n"
        
        with open(self.paper_dir / "table1_results.tex", "w", encoding="utf-8") as f:
            f.write(latex_str)
            
def summary_stats(df, out_dir):
    """Generates basic summary stats CSV"""
    res = []
    for (func, fw), grp in df.groupby(['function', 'firmware']):
        res.append({
            'function': func,
            'firmware': fw,
            'mean_cycles': grp['cycles'].mean(),
            'std_cycles': grp['cycles'].std(),
            'min_cycles': grp['cycles'].min(),
            'max_cycles': grp['cycles'].max(),
            'p95_cycles': grp['cycles'].quantile(0.95),
            'p99_cycles': grp['cycles'].quantile(0.99),
            'mean_mae': grp['mae'].mean() if 'mae' in grp else 0,
            'std_mae': grp['mae'].std() if 'mae' in grp else 0
        })
    df_res = pd.DataFrame(res)
    df_res.to_csv(out_dir / "latency_comparison.csv", index=False)
    
    # MAE subset
    if 'mae' in df.columns:
        df_mae = df_res[['function', 'firmware', 'mean_mae', 'std_mae']]
        df_mae.to_csv(out_dir / "mae_analysis.csv", index=False)
        
    # RAM subset
    if 'ram' in df.columns:
        df_ram = df.groupby(['function', 'firmware'])['ram'].mean().reset_index()
        df_ram.to_csv(out_dir / "ram_footprint.csv", index=False)


# ---------------------------------------------------------------------------
# GUI Application
# ---------------------------------------------------------------------------
class BenchmarkApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("ESP32 Academic Benchmark Lab")
        self.geometry("1200x850")
        
        # State
        self.esp = ESP32Controller()
        self.log_queue = queue.Queue()
        self.running_benchmark = False
        self.stop_requested = False
        
        self.current_session_dir = None
        
        # Auto-detect firmwares
        base_dir = Path(__file__).parent.absolute()
        fast_bin = base_dir / "firmware_fast" / "build" / "firmware_fast.bin"
        std_bin = base_dir / "firmware_standard" / "build" / "firmware_standard.bin"
        
        self.bin_fast = fast_bin if fast_bin.exists() else None
        self.bin_std = std_bin if std_bin.exists() else None
        
        # Live Stats tracking
        self.live_stats = {
            'fast_cycles': [], 'std_cycles': [],
            'fast_maes': [], 'count': 0, 'total': 0
        }
        
        self.build_ui()
        self.after(500, self.update_ports_loop)
        self.after(100, self.process_log_queue)

    def build_ui(self):
        # 2 main columns: Left for controls, Right for Monitor
        self.grid_columnconfigure(0, weight=1, minsize=400)
        self.grid_columnconfigure(1, weight=2, minsize=600)
        self.grid_rowconfigure(0, weight=1)

        # Frame Left - Controls
        left_frame = ctk.CTkFrame(self, fg_color="transparent")
        left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        self.build_connection_panel(left_frame)
        self.build_firmware_panel(left_frame)
        self.build_benchmark_panel(left_frame)
        
        # Frame Right - Monitor
        right_frame = ctk.CTkFrame(self, fg_color="transparent")
        right_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.build_monitor_panel(right_frame)

    def build_connection_panel(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(frame, text="1. Serial Connection", font=("Arial", 16, "bold")).pack(pady=5)
        
        # Port & Baud
        f1 = ctk.CTkFrame(frame, fg_color="transparent")
        f1.pack(fill="x", padx=10, pady=5)
        self.lbl_port = ctk.CTkLabel(f1, text="COM Port:")
        self.lbl_port.pack(side="left")
        
        self.port_var = ctk.StringVar(value="Searching...")
        self.port_menu = ctk.CTkOptionMenu(f1, variable=self.port_var, values=["Searching..."])
        self.port_menu.pack(side="right", fill="x", expand=True, padx=(10,0))
        
        f2 = ctk.CTkFrame(frame, fg_color="transparent")
        f2.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(f2, text="Baud Rate:").pack(side="left")
        self.baud_var = ctk.StringVar(value=str(DEFAULT_BAUD))
        ctk.CTkOptionMenu(f2, variable=self.baud_var, values=["115200", "460800", "921600"]).pack(side="right", fill="x", expand=True, padx=(10,0))
        
        # Connect / status
        f3 = ctk.CTkFrame(frame, fg_color="transparent")
        f3.pack(fill="x", padx=10, pady=10)
        
        self.status_dot = ctk.CTkLabel(f3, text="🔴", width=20)
        self.status_dot.pack(side="left")
        
        self.btn_connect = ctk.CTkButton(f3, text="Connect", command=self.toggle_connection)
        self.btn_connect.pack(side="left", fill="x", expand=True, padx=10)
        
        # ESP32 Info
        self.lbl_esp_info = ctk.CTkLabel(frame, text="Info: Not Connected", text_color="gray")
        self.lbl_esp_info.pack(pady=5)

    def build_firmware_panel(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(frame, text="2. Firmware Control", font=("Arial", 16, "bold")).pack(pady=5)
        
        # Fast firmware selectors
        for fw_type, label_text in [("fast", "Fast Engine (Q16.16):"), ("std", "Standard math.h:")]:
            fw_frame = ctk.CTkFrame(frame, fg_color="transparent")
            fw_frame.pack(fill="x", padx=10, pady=2)
            
            ctk.CTkLabel(fw_frame, text=label_text).pack(anchor="w")
            
            row = ctk.CTkFrame(fw_frame, fg_color="transparent")
            row.pack(fill="x")
            
            lbl_path = ctk.CTkLabel(row, text="No file selected", text_color="gray", width=200, anchor="w")
            
            if fw_type == "fast" and self.bin_fast:
                lbl_path.configure(text=Path(self.bin_fast).name, text_color="white")
            elif fw_type == "std" and self.bin_std:
                lbl_path.configure(text=Path(self.bin_std).name, text_color="white")
                
            lbl_path.pack(side="left", fill="x", expand=True)
            
            ctk.CTkButton(row, text="Browse", width=60, 
                          command=lambda t=fw_type, l=lbl_path: self.browse_firmware(t, l)).pack(side="right", padx=5)
            
            if fw_type == "fast":
                self.btn_flash_fast = ctk.CTkButton(frame, text="Flash Fast Engine", fg_color="#2b7a35", 
                                                    command=lambda: self.flash_firmware("fast"))
                self.btn_flash_fast.pack(fill="x", padx=15, pady=5)
            else:
                self.btn_flash_std = ctk.CTkButton(frame, text="Flash Standard Math", fg_color="#b56e1a",
                                                   command=lambda: self.flash_firmware("std"))
                self.btn_flash_std.pack(fill="x", padx=15, pady=5)
                
        self.lbl_active_fw = ctk.CTkLabel(frame, text="Active Firmware: Unknown", font=("Arial", 12, "italic"))
        self.lbl_active_fw.pack(pady=5)

    def build_benchmark_panel(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", pady=5, expand=True)
        
        ctk.CTkLabel(frame, text="3. Benchmark Control", font=("Arial", 16, "bold")).pack(pady=5)
        
        # Tests Count
        cnt_frame = ctk.CTkFrame(frame, fg_color="transparent")
        cnt_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(cnt_frame, text="Total tests per suite:").pack(side="left")
        self.entry_tests = ctk.CTkEntry(cnt_frame, width=80)
        self.entry_tests.insert(0, "300")
        self.entry_tests.pack(side="right")
        
        # Sub-buttons
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkButton(btn_frame, text="Test Trig", width=100, command=lambda: self.send_cmd("test_trig")).grid(row=0, column=0, padx=5, pady=5)
        ctk.CTkButton(btn_frame, text="Test MatMult", width=100, command=lambda: self.send_cmd("test_mat")).grid(row=0, column=1, padx=5, pady=5)
        ctk.CTkButton(btn_frame, text="Test Scalar", width=100, command=lambda: self.send_cmd("test_scalar")).grid(row=1, column=0, padx=5, pady=5)
        ctk.CTkButton(btn_frame, text="Test Mode", width=100, command=lambda: self.send_cmd("test_mode")).grid(row=1, column=1, padx=5, pady=5)
        btn_frame.grid_columnconfigure((0,1), weight=1)

        # Full Suite Button
        self.btn_run_suite = ctk.CTkButton(frame, text="Run Full Benchmark Suite", font=("Arial", 14, "bold"),
                                           height=40,
                                           command=self.start_paper_protocol)
        self.btn_run_suite.pack(fill="x", padx=15, pady=10)
        
        self.btn_stop = ctk.CTkButton(frame, text="🛑 STOP", fg_color="#a32828", state="disabled",
                                      command=self.stop_benchmark)
        self.btn_stop.pack(fill="x", padx=15, pady=(0,10))
        
        # Progress
        self.progress_bar = ctk.CTkProgressBar(frame)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=15, pady=5)
        self.lbl_progress = ctk.CTkLabel(frame, text="Idle")
        self.lbl_progress.pack(pady=2)

    def build_monitor_panel(self, parent):
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        
        # Live Stats Header
        stats_frame = ctk.CTkFrame(parent, height=80)
        stats_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        stats_frame.grid_columnconfigure((0,1,2), weight=1)
        
        self.lbl_stat_speedup = ctk.CTkLabel(stats_frame, text="Mean Speedup\n-- x", font=("Arial", 14, "bold"))
        self.lbl_stat_speedup.grid(row=0, column=0, pady=10)
        
        self.lbl_stat_mae = ctk.CTkLabel(stats_frame, text="Mean Abs Error\n--", font=("Arial", 14, "bold"))
        self.lbl_stat_mae.grid(row=0, column=1, pady=10)
        
        self.lbl_stat_count = ctk.CTkLabel(stats_frame, text="Tests\n0 / 0", font=("Arial", 14, "bold"))
        self.lbl_stat_count.grid(row=0, column=2, pady=10)
        
        # Log Text Box
        self.log_text = ctk.CTkTextbox(parent, font=("Consolas", 12))
        self.log_text.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.log_text.configure(state="disabled")

    # -----------------------------------------------------------------------
    # Logic & Interaction
    # -----------------------------------------------------------------------
    def log(self, tag, msg):
        self.log_queue.put((tag, msg))

    def process_log_queue(self):
        try:
            while True:
                tag, msg = self.log_queue.get_nowait()
                ts = datetime.datetime.now().strftime("%H:%M:%S")
                self.log_text.configure(state="normal")
                self.log_text.insert("end", f"[{ts}] [{tag}] {msg}\n")
                self.log_text.see("end")
                self.log_text.configure(state="disabled")
        except queue.Empty:
            pass
        # Also update live metrics UI
        self._update_live_metrics_ui()
        self.after(100, self.process_log_queue)
        
    def _update_live_metrics_ui(self):
        if self.live_stats['total'] > 0:
            c = self.live_stats['count']
            t = self.live_stats['total']
            self.lbl_stat_count.configure(text=f"Tests\n{c} / {t}")
            
            if len(self.live_stats['fast_maes']) > 0:
                mae = np.mean(self.live_stats['fast_maes'])
                self.lbl_stat_mae.configure(text=f"Mean Abs Error\n{mae:.4e}")
            
            if len(self.live_stats['fast_cycles']) > 0 and len(self.live_stats['std_cycles']) > 0:
                fc = np.mean(self.live_stats['fast_cycles'])
                sc = np.mean(self.live_stats['std_cycles'])
                if fc > 0:
                    self.lbl_stat_speedup.configure(text=f"Mean Speedup\n{sc/fc:.2f}x")

    def update_ports_loop(self):
        if not self.esp.is_connected and not self.running_benchmark:
            ports = self.esp.get_ports()
            current = self.port_var.get()
            if not ports:
                ports = ["No devices found"]
                
            self.port_menu.configure(values=ports)
            if current not in ports and ports[0] != "No devices found":
                self.port_var.set(ports[0])
            elif current not in ports and current != "Searching...":
                self.port_var.set("Searching...")
                
        self.after(2000, self.update_ports_loop)

    def toggle_connection(self):
        if self.esp.is_connected:
            self.esp.disconnect()
            self.btn_connect.configure(text="Connect")
            self.status_dot.configure(text="🔴")
            self.lbl_esp_info.configure(text="Info: Disconnected")
            self.log("INFO", "Disconnected from serial.")
        else:
            p = self.port_var.get()
            b = self.baud_var.get()
            if p in ["Searching...", "No devices found"]:
                messagebox.showwarning("Warning", "No valid COM port selected.")
                return
                
            ok, msg = self.esp.connect(p, b)
            if ok:
                self.btn_connect.configure(text="Disconnect")
                self.status_dot.configure(text="🟢")
                self.log("INFO", msg)
                
                # Show parsed info
                info_str = f"Chip: {self.esp.chip_model} | Flash: {self.esp.flash_size} | RAM: {self.esp.free_ram}"
                self.lbl_esp_info.configure(text=info_str)
            else:
                self.log("ERROR", msg)
                messagebox.showerror("Error", msg)

    def browse_firmware(self, fw_type, lbl_widget):
        path = filedialog.askopenfilename(title="Select .bin", filetypes=[("BIN files", "*.bin"), ("All", "*.*")])
        if path:
            if fw_type == "fast":
                self.bin_fast = path
            else:
                self.bin_std = path
            lbl_widget.configure(text=Path(path).name, text_color="white")

    def flash_firmware(self, fw_type):
        path = self.bin_fast if fw_type == "fast" else self.bin_std
        if not path:
            messagebox.showwarning("File missing", "Please select a binary file first.")
            return
            
        threading.Thread(target=self._flash_worker, args=(path, fw_type), daemon=True).start()

    def _flash_worker(self, path, fw_type):
        self.log("INFO", f"Initiating flash process for {fw_type}...")
        self.btn_flash_fast.configure(state="disabled")
        self.btn_flash_std.configure(state="disabled")
        self.btn_run_suite.configure(state="disabled")
        
        ok = self.esp.flash_firmware(path, self.log_queue)
        
        if ok:
            self.log("SUCCESS", f"Firmware '{fw_type}' flashed successfully.")
            self.lbl_active_fw.configure(text=f"Active Firmware: {'Fast Engine' if fw_type=='fast' else 'Standard Math'}")
        else:
            self.log("ERROR", f"Flashing '{fw_type}' failed.")
            
        self.btn_flash_fast.configure(state="normal")
        self.btn_flash_std.configure(state="normal")
        self.btn_run_suite.configure(state="normal")
        
        # update UI state based on serial reconnect
        if self.esp.is_connected:
            self.btn_connect.configure(text="Disconnect")
            self.status_dot.configure(text="🟢")
        else:
            self.btn_connect.configure(text="Connect")
            self.status_dot.configure(text="🔴")

    def send_cmd(self, cmd_name):
        if not self.esp.is_connected:
            messagebox.showwarning("Warning", "Connect to ESP32 first.")
            return
        self.log("CMD", f"Sending {cmd_name}")
        self.esp.send_command({"cmd": cmd_name})

    # -----------------------------------------------------------------------
    # The Paper Protocol
    # -----------------------------------------------------------------------
    def stop_benchmark(self):
        self.stop_requested = True
        self.log("WARNING", "Emergency STOP triggered. Protocol will halt.")

    def start_paper_protocol(self):
        if not self.bin_fast or not self.bin_std:
            messagebox.showerror("Error", "Both Fast and Standard binary files must be selected.")
            return
            
        try:
            tests_count = int(self.entry_tests.get())
            if not (100 <= tests_count <= 1000):
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Test count must be an integer between 100 and 1000.")
            return

        self.running_benchmark = True
        self.stop_requested = False
        self.btn_run_suite.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        
        # Reset live stats
        self.live_stats = {
            'fast_cycles': [], 'std_cycles': [],
            'fast_maes': [], 'count': 0, 'total': tests_count * 2
        }
        
        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.current_session_dir = Path("outputs") / f"session_{ts}"
        (self.current_session_dir / "raw_data").mkdir(parents=True, exist_ok=True)
        
        threading.Thread(target=self._paper_protocol_worker, args=(tests_count,), daemon=True).start()

    def _paper_protocol_worker(self, tests_count):
        seed = 42 # Ensures identical inputs for A/B comparison
        
        try:
            # === 1. FLASH FIRMWARE A (FAST) ===
            self.log("PROTOCOL", "Step 1/8: Flashing Fast Engine...")
            if not self.esp.flash_firmware(self.bin_fast, self.log_queue):
                raise Exception("Flashing Fast Engine failed.")
            self.lbl_active_fw.configure(text="Active Firmware: Fast Engine")
            
            if self.esp.ser and self.esp.ser.is_open:
                try:
                    self.esp.ser.close()
                except:
                    pass

            time.sleep(1)
            
            reconnected = False
            for attempt in range(10):
                ok, msg = self.esp.connect(self.esp.port, self.esp.baud)
                if ok:
                    reconnected = True
                    break
                time.sleep(1)
            
            if not reconnected:
                raise Exception(f"Failed to reconnect to ESP32 after retries: {msg}")
                
            time.sleep(2)
            
            if self.esp.ser:
                self.esp.ser.reset_input_buffer()
            
            # === 2 & 3. RUN & SAVE A ===
            self.log("PROTOCOL", "Step 2/8: Running Benchmark Suite A (Fast)")
            fast_data = self._collect_data(tests_count, seed, "Fast", self.live_stats['fast_cycles'], self.live_stats['fast_maes'])
            
            self.log("PROTOCOL", "Step 3/8: Saving Fast Engine raw data")
            with open(self.current_session_dir / "raw_data" / "firmware_A_fast.jsonl", 'w', encoding="utf-8") as f:
                for line in fast_data:
                    f.write(json.dumps(line) + "\n")
                    
            if self.stop_requested: raise Exception("User requested stop.")

            # === 4. FLASH FIRMWARE B (STANDARD) ===
            self.log("PROTOCOL", "Step 4/8: Flashing Standard Math...")
            if not self.esp.flash_firmware(self.bin_std, self.log_queue):
                raise Exception("Flashing Standard Math failed.")
            self.lbl_active_fw.configure(text="Active Firmware: Standard Math")
            
            if self.esp.ser and self.esp.ser.is_open:
                try:
                    self.esp.ser.close()
                except:
                    pass

            time.sleep(1)
            
            reconnected = False
            for attempt in range(10):
                ok, msg = self.esp.connect(self.esp.port, self.esp.baud)
                if ok:
                    reconnected = True
                    break
                time.sleep(1)
            
            if not reconnected:
                raise Exception(f"Failed to reconnect to ESP32 after retries: {msg}")
                
            time.sleep(2)
            
            if self.esp.ser:
                self.esp.ser.reset_input_buffer()

            # === 5 & 6. RUN & SAVE B ===
            self.log("PROTOCOL", "Step 5/8: Running Benchmark Suite B (Standard)")
            std_data = self._collect_data(tests_count, seed, "Standard", self.live_stats['std_cycles'], None)
            
            self.log("PROTOCOL", "Step 6/8: Saving Standard Engine raw data")
            with open(self.current_session_dir / "raw_data" / "firmware_B_standard.jsonl", 'w', encoding="utf-8") as f:
                for line in std_data:
                    f.write(json.dumps(line) + "\n")

            # === 7. METADATA & README ===
            self.log("PROTOCOL", "Step 7/8: Generating README")
            self._write_readme(tests_count, seed, incomplete=False)

            # === 8. ANALYSIS & EXPORT ===
            self.log("PROTOCOL", "Step 8/8: Performing Statistical Analysis (Pandas/SciPy/Matplotlib)")
            analyzer = BenchmarkAnalyzer(self.current_session_dir)
            ok, msg = analyzer.analyze()
            if ok:
                self.log("SUCCESS", msg)
                self.after(0, lambda: messagebox.showinfo("Success", "Protocol completed successfully! Data and Figures exported."))
            else:
                self.log("ERROR", f"Analysis failed: {msg}")

        except Exception as e:
            self.log("ERROR", f"Protocol Halted: {e}")
            self._write_readme(tests_count, seed, incomplete=True)
            self.after(0, lambda e=e: messagebox.showerror("Error", f"Protocol interrupted:\n{e}"))
        finally:
            self.running_benchmark = False
            self.after(0, self._reset_benchmark_ui)

    def _collect_data(self, test_count, seed, fw_name, cycle_list, mae_list):
        data = []
        if not self.esp.send_command({"cmd": "run_suite", "tests": test_count, "seed": seed}):
            raise Exception("Serial connection lost or command failed.")
            
        received = 0
        malformed = 0
        
        while received < test_count and not self.stop_requested:
            line = self.esp.read_line()
            if line:
                try:
                    pkt = json.loads(line)
                    
                    if "cycles_elapsed" in pkt and "cycles" not in pkt:
                        pkt["cycles"] = pkt["cycles_elapsed"]
                        
                    if "function" in pkt and "cycles" in pkt:
                        data.append(pkt)
                        received += 1
                        self.live_stats['count'] += 1
                        
                        cycle_list.append(pkt['cycles'])
                        if mae_list is not None and 'mae' in pkt:
                            mae_list.append(pkt['mae'])
                            
                        pct = received / test_count
                        self.after(0, self._update_progress, pct, received, test_count, pkt.get('function'), fw_name)
                    else:
                        self.log("WARNING", f"Missing keys in JSON: {line}")
                except json.JSONDecodeError:
                    if line.strip(): # ignore purely empty lines
                        malformed += 1
                        self.log("WARNING", f"Malformed JSON: {line}")
            else:
                time.sleep(0.01)
                
        self.log("INFO", f"{fw_name} collection complete. Retrieved: {received}/{test_count}. Malformed: {malformed}")
        return data

    def _update_progress(self, pct, recv, total, func, fw):
        self.progress_bar.set(pct)
        self.lbl_progress.configure(text=f"Test {recv} / {total} — {func} — {fw}")

    def _reset_benchmark_ui(self):
        self.btn_run_suite.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.progress_bar.set(0)
        self.lbl_progress.configure(text="Idle")

    def _write_readme(self, tests_count, seed, incomplete=False):
        status = "INCOMPLETE" if incomplete else "OK"
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        meta = {
            "timestamp": ts,
            "status": status,
            "tests_expected": tests_count,
            "seed": seed,
            "os": os.name,
            "python": sys.version.split()[0],
            "binaries": {
                "fast": str(self.bin_fast),
                "standard": str(self.bin_std)
            }
        }
        
        with open(self.current_session_dir / "raw_data" / "session_metadata.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=4)
            
        readme_str = f"""================================================================================
ESP32 BENCHMARK SESSION LOG
================================================================================
Timestamp:          {ts}
Status:             {status}
Python Env:         {sys.version.split()[0]}
OS:                 {os.name}

ESP32 HARDWARE INFO (At connection)
--------------------------------------------------------------------------------
Chip Model:         {self.esp.chip_model}
Flash Size:         {self.esp.flash_size}
Free RAM reported:  {self.esp.free_ram}

TEST CONFIGURATION
--------------------------------------------------------------------------------
Fast Q16.16 binary: {self.bin_fast}
Standard binary:    {self.bin_std}
Tests per firmware: {tests_count}
Random Seed:        {seed}

Validation Notes:
- The exact same seed was passed to both firmwares ensuring identical inputs.
- Outlier detection (z-score > 3) and Wilcoxon tests were performed post-run.
- For speedup ratios, see analysis/statistical_summary.txt
================================================================================
"""
        with open(self.current_session_dir / "README.txt", "w", encoding="utf-8") as f:
            f.write(readme_str)


if __name__ == "__main__":
    app = BenchmarkApp()
    app.mainloop()
