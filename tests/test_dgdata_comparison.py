"""Comprehensive comparison and parity tests between Pure Python DGDATA and NumPy DGDATA.

Includes:
- Cross-encoding and cross-decoding verification across small, medium, large, and real save payloads.
- Bit-for-bit checksum parity tests.
- 100-run performance benchmark measuring encode/decode latency and generating comparison graphs.
"""

import json
import os
import random
import string
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

try:
    import tests.dgdata_numpy as numpy_dgdata
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

import lib.crypt.dgdata as pure_dgdata


@unittest.skipUnless(HAS_NUMPY, "NumPy is not installed")
class TestDGDataComparison(unittest.TestCase):
    """Tests functional parity and cross-compatibility between Pure Python and NumPy implementations."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.save_path = Path(__file__).resolve().parent.parent / "Profile.save"
        if cls.save_path.exists():
            with open(cls.save_path, "rb") as f:
                cls.real_save_bytes = f.read()
            cls.real_save_str = pure_dgdata.decode_bytes(cls.real_save_bytes)
        else:
            sample_dict = {
                "Version": 4,
                "Inventory": {
                    f"Profile{i}": {
                        "Name": f"Character_{i}",
                        "Money": 1000000 + i * 5000,
                        "Level": 50 + i,
                        "Skills": [1, 2, 3, 4, 5],
                    }
                    for i in range(10)
                },
            }
            cls.real_save_str = json.dumps(sample_dict, indent=2)
            cls.real_save_bytes = pure_dgdata.encode_bytes(cls.real_save_str)

    def test_pure_to_numpy_cross_decode(self) -> None:
        """Data encoded with Pure Python must decode identically with NumPy."""
        encoded_pure = pure_dgdata.encode_bytes(self.real_save_str)
        decoded_numpy = numpy_dgdata.decode_bytes(encoded_pure)
        self.assertEqual(decoded_numpy, self.real_save_str)

    def test_numpy_to_pure_cross_decode(self) -> None:
        """Data encoded with NumPy must decode identically with Pure Python."""
        encoded_numpy = numpy_dgdata.encode_bytes(self.real_save_str)
        decoded_pure = pure_dgdata.decode_bytes(encoded_numpy)
        self.assertEqual(decoded_pure, self.real_save_str)

    def test_exact_byte_parity_across_sizes(self) -> None:
        """Both implementations must produce bit-for-bit identical encrypted bytes."""
        test_sizes = [0, 1, 6, 7, 13, 64, 512, 4096, 65536, 200000]
        for size in test_sizes:
            payload = "".join(random.choices(string.ascii_letters + string.digits + " \n\t{}", k=size))
            encoded_pure = pure_dgdata.encode_bytes(payload)
            encoded_numpy = numpy_dgdata.encode_bytes(payload)
            self.assertEqual(
                encoded_pure,
                encoded_numpy,
                f"Byte mismatch on payload of size {size}",
            )
            # Verify checksums match exactly
            self.assertEqual(encoded_pure[6:14], encoded_numpy[6:14])

    def test_file_io_parity(self) -> None:
        """Test encode_to_file and decode_from_file parity on disk."""
        with tempfile.NamedTemporaryFile(suffix=".save", delete=False) as f_pure, \
             tempfile.NamedTemporaryFile(suffix=".save", delete=False) as f_numpy:
            path_pure = f_pure.name
            path_numpy = f_numpy.name

        try:
            pure_dgdata.encode_to_file(self.real_save_str, path_pure)
            numpy_dgdata.encode_to_file(self.real_save_str, path_numpy)

            with open(path_pure, "rb") as fp, open(path_numpy, "rb") as fn:
                self.assertEqual(fp.read(), fn.read())

            # Cross-decode from file
            decoded_via_numpy = numpy_dgdata.decode_from_file(path_pure)
            decoded_via_pure = pure_dgdata.decode_from_file(path_numpy)

            self.assertEqual(decoded_via_numpy, self.real_save_str)
            self.assertEqual(decoded_via_pure, self.real_save_str)
        finally:
            if os.path.exists(path_pure):
                os.remove(path_pure)
            if os.path.exists(path_numpy):
                os.remove(path_numpy)

    def test_error_handling_parity(self) -> None:
        """Corrupt headers and checksum mismatches should raise DGDataDecodeError in both."""
        invalid_header = b"BADMAG12345678payload"
        with self.assertRaises(pure_dgdata.DGDataDecodeError):
            pure_dgdata.decode_bytes(invalid_header)
        with self.assertRaises(numpy_dgdata.DGDataDecodeError):
            numpy_dgdata.decode_bytes(invalid_header)

        # Corrupt checksum
        valid_encoded = pure_dgdata.encode_bytes("test_payload")
        corrupted = valid_encoded[:6] + b"00000000" + valid_encoded[14:]
        with self.assertRaises(pure_dgdata.DGDataDecodeError):
            pure_dgdata.decode_bytes(corrupted)
        with self.assertRaises(numpy_dgdata.DGDataDecodeError):
            numpy_dgdata.decode_bytes(corrupted)

    def test_100_runs_benchmark_and_generate_graph(self) -> None:
        """Runs 100 encode/decode benchmark iterations across Baseline, NumPy, and Optimized DGDATA."""
        iterations = 100
        payload_str = self.real_save_str
        payload_bytes = self.real_save_bytes
        payload_size_kb = len(payload_bytes) / 1024.0

        # Legacy baseline implementation for comparison
        def legacy_encode(data: str) -> bytes:
            data_b = data.encode()
            h = pure_dgdata.DGDataHash()
            h.update(data_b)
            encoded = bytes((b + (21 + i % 6)) & 0xFF for i, b in enumerate(data_b))
            chk = f"{h.digest:08x}".encode()
            return b"DGDATA" + chk + encoded

        def legacy_decode(raw: bytes) -> str:
            h = pure_dgdata.DGDataHash()
            data_payload = raw[14:]
            decoded = bytes((b - (21 + i % 6)) & 0xFF for i, b in enumerate(data_payload))
            h.update(decoded)
            chk = f"{h.digest:08x}".encode()
            if chk != raw[6:14]:
                raise pure_dgdata.DGDataDecodeError("Checksum error")
            return decoded.decode()

        # Warmup
        for _ in range(5):
            _ = legacy_encode(payload_str)
            _ = legacy_decode(payload_bytes)
            _ = pure_dgdata.encode_bytes(payload_str)
            _ = pure_dgdata.decode_bytes(payload_bytes)
            _ = numpy_dgdata.encode_bytes(payload_str)
            _ = numpy_dgdata.decode_bytes(payload_bytes)

        legacy_encode_times: list[float] = []
        legacy_decode_times: list[float] = []
        numpy_encode_times: list[float] = []
        numpy_decode_times: list[float] = []
        optimized_encode_times: list[float] = []
        optimized_decode_times: list[float] = []

        # Run 100 iterations
        for _ in range(iterations):
            # 1. Legacy Baseline
            t0 = time.perf_counter_ns()
            _ = legacy_encode(payload_str)
            legacy_encode_times.append((time.perf_counter_ns() - t0) / 1_000_000.0)

            t0 = time.perf_counter_ns()
            _ = legacy_decode(payload_bytes)
            legacy_decode_times.append((time.perf_counter_ns() - t0) / 1_000_000.0)

            # 2. NumPy Vectorized
            t0 = time.perf_counter_ns()
            _ = numpy_dgdata.encode_bytes(payload_str)
            numpy_encode_times.append((time.perf_counter_ns() - t0) / 1_000_000.0)

            t0 = time.perf_counter_ns()
            _ = numpy_dgdata.decode_bytes(payload_bytes)
            numpy_decode_times.append((time.perf_counter_ns() - t0) / 1_000_000.0)

            # 3. Optimized DGDATA (Slicing Table Hash + 6-Phase Vectorized Translation)
            t0 = time.perf_counter_ns()
            _ = pure_dgdata.encode_bytes(payload_str)
            optimized_encode_times.append((time.perf_counter_ns() - t0) / 1_000_000.0)

            t0 = time.perf_counter_ns()
            _ = pure_dgdata.decode_bytes(payload_bytes)
            optimized_decode_times.append((time.perf_counter_ns() - t0) / 1_000_000.0)

        # Compute Statistics
        def calc_stats(times: list[float]) -> dict[str, float]:
            sorted_t = sorted(times)
            mean_val = sum(times) / len(times)
            variance = sum((x - mean_val) ** 2 for x in times) / len(times)
            return {
                "mean": mean_val,
                "median": sorted_t[len(sorted_t) // 2],
                "min": sorted_t[0],
                "max": sorted_t[-1],
                "p95": sorted_t[int(len(sorted_t) * 0.95)],
                "p99": sorted_t[int(len(sorted_t) * 0.99)],
                "std": variance ** 0.5,
            }

        legacy_enc_stats = calc_stats(legacy_encode_times)
        legacy_dec_stats = calc_stats(legacy_decode_times)
        numpy_enc_stats = calc_stats(numpy_encode_times)
        numpy_dec_stats = calc_stats(numpy_decode_times)
        opt_enc_stats = calc_stats(optimized_encode_times)
        opt_dec_stats = calc_stats(optimized_decode_times)

        # Plot 4-Panel Visualization if matplotlib is installed
        output_paths = [
            Path(__file__).resolve().parent / "dgdata_benchmark_100_runs.png",
            Path("/home/admin/.gemini/antigravity-ide/brain/343c27c9-e345-4bd5-a218-faa866d9ed9b/dgdata_benchmark.png"),
        ]

        if HAS_MATPLOTLIB:
            plt.style.use("seaborn-v0_8-darkgrid" if "seaborn-v0_8-darkgrid" in plt.style.available else "default")
            fig, axs = plt.subplots(2, 2, figsize=(16, 11), dpi=150)
            fig.suptitle(
                f"DGDATA 3-Way Speed Benchmark: Baseline vs NumPy vs Optimized Architecture\n(100 Iterations on {payload_size_kb:.1f} KB Save File)",
                fontsize=15,
                fontweight="bold",
                y=0.98,
            )

            runs = list(range(1, iterations + 1))

            # Panel 1: Encode Latency Timeline
            ax1 = axs[0, 0]
            ax1.plot(runs, legacy_encode_times, label=f"Legacy Baseline (Mean: {legacy_enc_stats['mean']:.2f} ms)", color="#e74c3c", alpha=0.7, linestyle="--", linewidth=1.2)
            ax1.plot(runs, numpy_encode_times, label=f"NumPy Vectorized (Mean: {numpy_enc_stats['mean']:.2f} ms)", color="#3498db", alpha=0.85, linewidth=1.5)
            ax1.plot(runs, optimized_encode_times, label=f"Optimized DGDATA (Mean: {opt_enc_stats['mean']:.2f} ms)", color="#2ecc71", alpha=0.95, linewidth=2.0)
            ax1.set_title("Encode Latency (100 Runs)", fontweight="bold")
            ax1.set_xlabel("Iteration")
            ax1.set_ylabel("Execution Time (ms)")
            ax1.legend(loc="upper right", frameon=True)

            # Panel 2: Decode Latency Timeline
            ax2 = axs[0, 1]
            ax2.plot(runs, legacy_decode_times, label=f"Legacy Baseline (Mean: {legacy_dec_stats['mean']:.2f} ms)", color="#e67e22", alpha=0.7, linestyle="--", linewidth=1.2)
            ax2.plot(runs, numpy_decode_times, label=f"NumPy Vectorized (Mean: {numpy_dec_stats['mean']:.2f} ms)", color="#3498db", alpha=0.85, linewidth=1.5)
            ax2.plot(runs, optimized_decode_times, label=f"Optimized DGDATA (Mean: {opt_dec_stats['mean']:.2f} ms)", color="#2ecc71", alpha=0.95, linewidth=2.0)
            ax2.set_title("Decode Latency (100 Runs)", fontweight="bold")
            ax2.set_xlabel("Iteration")
            ax2.set_ylabel("Execution Time (ms)")
            ax2.legend(loc="upper right", frameon=True)

            # Panel 3: Box Plot Distribution
            ax3 = axs[1, 0]
            box_data = [
                legacy_encode_times, numpy_encode_times, optimized_encode_times,
                legacy_decode_times, numpy_decode_times, optimized_decode_times,
            ]
            box_labels = ["Baseline\nEnc", "NumPy\nEnc", "Optimized\nEnc", "Baseline\nDec", "NumPy\nDec", "Optimized\nDec"]
            box_colors = ["#e74c3c", "#3498db", "#2ecc71", "#e67e22", "#3498db", "#2ecc71"]
            bplot = ax3.boxplot(box_data, patch_artist=True, tick_labels=box_labels, showmeans=True)
            for patch, color in zip(bplot["boxes"], box_colors):
                patch.set_facecolor(color)
                patch.set_alpha(0.75)
            ax3.set_title("Latency Distribution & Variance", fontweight="bold")
            ax3.set_ylabel("Execution Time (ms)")

            # Panel 4: Summary Bar Chart & Speedup
            ax4 = axs[1, 1]
            categories = ["Encode Time", "Decode Time"]
            baseline_means = [legacy_enc_stats["mean"], legacy_dec_stats["mean"]]
            numpy_means = [numpy_enc_stats["mean"], numpy_dec_stats["mean"]]
            opt_means = [opt_enc_stats["mean"], opt_dec_stats["mean"]]

            x = [0, 1]
            width = 0.25
            rects1 = ax4.bar([i - width for i in x], baseline_means, width, label="Legacy Baseline", color="#e74c3c", alpha=0.8)
            rects2 = ax4.bar(x, numpy_means, width, label="NumPy Vectorized", color="#3498db", alpha=0.85)
            rects3 = ax4.bar([i + width for i in x], opt_means, width, label="Optimized Architecture", color="#2ecc71", alpha=0.95)

            speedup_enc_base = legacy_enc_stats["mean"] / opt_enc_stats["mean"]
            speedup_enc_numpy = numpy_enc_stats["mean"] / opt_enc_stats["mean"]
            speedup_dec_base = legacy_dec_stats["mean"] / opt_dec_stats["mean"]
            speedup_dec_numpy = numpy_dec_stats["mean"] / opt_dec_stats["mean"]

            ax4.set_xticks(x)
            ax4.set_xticklabels(categories)
            ax4.set_ylabel("Mean Execution Time (ms)")
            ax4.set_title("Mean Latency Comparison & Optimization", fontweight="bold")
            ax4.legend(loc="upper left", frameon=True)

            for rect in list(rects1) + list(rects2) + list(rects3):
                h = rect.get_height()
                ax4.annotate(f"{h:.2f}ms", xy=(rect.get_x() + rect.get_width() / 2, h), xytext=(0, 4), textcoords="offset points", ha="center", va="bottom", fontsize=8, fontweight="bold")

            ax4.text(
                0,
                max(baseline_means) * 0.45,
                f"Optimized Speedup:\n{speedup_enc_base:.2f}x vs Baseline\n{speedup_enc_numpy:.2f}x vs NumPy",
                ha="center",
                fontsize=9,
                fontweight="bold",
                bbox={"boxstyle": "round,pad=0.3", "fc": "#a8f0c6", "alpha": 0.8},
            )
            ax4.text(
                1,
                max(baseline_means) * 0.45,
                f"Optimized Speedup:\n{speedup_dec_base:.2f}x vs Baseline\n{speedup_dec_numpy:.2f}x vs NumPy",
                ha="center",
                fontsize=9,
                fontweight="bold",
                bbox={"boxstyle": "round,pad=0.3", "fc": "#a8f0c6", "alpha": 0.8},
            )

            plt.tight_layout(rect=(0.0, 0.03, 1.0, 0.95))

            for p in output_paths:
                p.parent.mkdir(parents=True, exist_ok=True)
                fig.savefig(str(p), format="png")

            plt.close(fig)

        # Store stats on self for assertion & reporting
        self.benchmark_results: dict[str, Any] = {
            "legacy_encode": legacy_enc_stats,
            "legacy_decode": legacy_dec_stats,
            "numpy_encode": numpy_enc_stats,
            "numpy_decode": numpy_dec_stats,
            "optimized_encode": opt_enc_stats,
            "optimized_decode": opt_dec_stats,
            "speedup_vs_baseline_enc": legacy_enc_stats["mean"] / opt_enc_stats["mean"],
            "speedup_vs_numpy_enc": numpy_enc_stats["mean"] / opt_enc_stats["mean"],
            "speedup_vs_baseline_dec": legacy_dec_stats["mean"] / opt_dec_stats["mean"],
            "speedup_vs_numpy_dec": numpy_dec_stats["mean"] / opt_dec_stats["mean"],
            "chart_path": str(output_paths[0]),
        }

        self.assertGreater(len(optimized_encode_times), 0)
        self.assertGreater(len(numpy_encode_times), 0)
        self.assertLess(opt_enc_stats["mean"], legacy_enc_stats["mean"])
        self.assertLess(opt_dec_stats["mean"], legacy_dec_stats["mean"])


if __name__ == "__main__":
    unittest.main()
