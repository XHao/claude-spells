# JFR Results Interpretation Guide

Thresholds and diagnostic rules for interpreting JFR analysis output.

## GC

| Condition | Severity | Action |
|-----------|----------|--------|
| GC Max > 500ms | High | Risk of application stall; investigate allocation hot paths |
| GC P99 > 200ms | Medium | Significant tail latency impact; review heap size and GC policy |
| GC P99 > 100ms | Low | Monitor; may indicate heap pressure under load |
| Old Gen GC count > 0 | High | Full GC occurred; check for memory leaks or undersized heap |

## Memory Allocation

| Condition | Severity | Action |
|-----------|----------|--------|
| Single thread > 30% of total allocation | High | Memory pressure concentrated; check top allocating classes |
| Top allocating class is byte[] or char[] | Medium | String-heavy workload; consider string interning or pooling |
| Allocation outside TLAB frequent | Medium | Large object allocations; consider increasing TLAB size |

## Lock Contention

| Condition | Severity | Action |
|-----------|----------|--------|
| Single lock wait ≥ 100ms | High | Severe contention; reduce lock scope or use lock-free structures |
| Single lock wait 10–100ms | Medium | Noticeable contention; profile under load to confirm |
| Total lock wait > 10% of wall time | High | Structural concurrency bottleneck |

## I/O

| Condition | Severity | Action |
|-----------|----------|--------|
| File operation ≥ 100ms | High | Slow disk; check path and consider async I/O |
| Socket operation ≥ 100ms | High | Network latency or remote service slowness |
| File operation 10–100ms | Medium | Monitor; may be acceptable for batch operations |

## CPU Hotspots

| Condition | Severity | Action |
|-----------|----------|--------|
| Single method > 20% CPU samples | High | Dominant hotspot; profile call chain for optimization |
| GC-related frames > 10% CPU | High | GC competing with application threads |
| JIT compiler frames > 5% | Medium | Warm-up phase or frequent deoptimization |

## Thread Activity

| Condition | Severity | Action |
|-----------|----------|--------|
| Thread count > 500 | Medium | Review thread pool sizing |
| Single thread > 50% of CPU samples | High | Single-threaded bottleneck; check for serialization points |
| Many threads with 0 CPU samples | Low | Idle thread pool; may indicate over-provisioning |
