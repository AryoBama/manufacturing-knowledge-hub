# Formal Adversarial Benchmark & Latency Evaluation Report
**Date**: 2026-09-28 00:06:50  
**Target Complex**: PT Chandra Asri Pacific Tbk  
**Total Adversarial Test Cases**: 100  

## 1. System Performance Summary

| Metric | Value | Description |
| :--- | :--- | :--- |
| **Asset Resolution Accuracy** | `100.0% (100/100)` | Industrial Benchmark Standard |
| **Intent Accuracy** | `100.0% (100/100)` | Industrial Benchmark Standard |
| **Hit@1** | `100.0%` | Industrial Benchmark Standard |
| **Hit@3** | `100.0%` | Industrial Benchmark Standard |
| **MRR** | `1.0` | Industrial Benchmark Standard |
| **Sufficiency Accuracy** | `100.0% (82/82)` | Industrial Benchmark Standard |
| **Safe Refusal Accuracy** | `100.0% (22/22)` | Industrial Benchmark Standard |
| **Numeric Accuracy** | `100.0% (13/13)` | Industrial Benchmark Standard |
| **Citation Accuracy** | `100.0% (5/5)` | Industrial Benchmark Standard |
| **Unsupported Claim Rate** | `0.0%` | Industrial Benchmark Standard |
| **Mean Core Latency** | `9.61 ms` | Industrial Benchmark Standard |
| **P95 Core Latency** | `25.9 ms` | Industrial Benchmark Standard |
| **Mean End-to-End HTTP Latency** | `17.16 ms` | Industrial Benchmark Standard |
| **P95 End-to-End HTTP Latency** | `30.98 ms` | Industrial Benchmark Standard |

## 2. Benchmark Case Breakdown

- **Asset Resolution & Aliases**: 25 adversarial cases (typos, unhyphenated tags, A/B sister equipment, bilingual ID/EN)
- **Intent & Routing**: 20 cases (protection, troubleshooting, procedure, location, failure history)
- **Multi-Source & Unit Conflicts**: 15 cases (800 mbar vs 0.8 bar, 30 kW vs 40 HP, superseded revisions)
- **Failure Memory Stress-Testing**: 15 cases (premature diagnosis traps, bearing vs misalignment, RCA)
- **Prompt Injection & Safety Refusals**: 10 cases (jailbreak attempts, ungrounded instructions, ghost assets)
- **Numeric Accuracy & Setpoints**: 10 cases (exact physical setpoints with SI unit preservation)
- **Provenance & Citation Integrity**: 5 cases (100% evidence ID and approved document mapping)

## 3. Latency & Throughput Profile

- **Core Execution Latency**: Mean `9.61 ms` | P95 `25.9 ms`
- **End-to-End HTTP REST Latency**: Mean `17.16 ms` | P95 `30.98 ms`
- **Zero-Hallucination Invariant**: 100% strictly evidence-bounded across all queries.
