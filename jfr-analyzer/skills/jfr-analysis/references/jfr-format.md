# JFR Text Export Format Reference

This reference covers the event types and field formats present in JFR text exports (produced by tools like `jfr print --json` or converted via JMC).

## Key Event Types

### jdk.ExecutionSample
CPU profiling sample. Captured at a fixed interval on RUNNABLE threads.

```
jdk.ExecutionSample {
  startTime = 14:10:21.961 (2026-03-06)
  sampledThread = "thread-name" (javaThreadId = 376)
  state = "STATE_RUNNABLE"
  stackTrace = [
    some.package.ClassName.methodName(ArgType) line: 123
    ...
  ]
}
```

**Key fields**: `sampledThread`, `state`, `stackTrace`

### jdk.ObjectAllocationSample
Sampled object allocation (TLAB-based, weighted by allocation size).

```
jdk.ObjectAllocationSample {
  startTime = 14:09:01.838
  objectClass = byte[] (classLoader = bootstrap)
  weight = 1.4 kB
  eventThread = "thread-name" (javaThreadId = 376)
  stackTrace = [ ... ]
}
```

**Key fields**: `objectClass`, `weight` (approximate allocated bytes), `eventThread`

### jdk.ObjectAllocationOutsideTLAB
Large object allocation (outside TLAB — exact size recorded).

```
jdk.ObjectAllocationOutsideTLAB {
  objectClass = byte[]
  allocationSize = 1048576
  eventThread = "..."
}
```

**Key fields**: `objectClass`, `allocationSize` (exact bytes)

### jdk.GCPhasePause / jdk.GarbageCollection
GC pause event.

```
jdk.GCPhasePause {
  startTime = ...
  duration = 42.00 ms
  gcId = 1234
  name = "G1 Young Generation"
}
```

**Key fields**: `duration` (ms)

### jdk.ThreadAllocationStatistics
Cumulative allocation per thread since JVM start. Snapshot event.

```
jdk.ThreadAllocationStatistics {
  startTime = ...
  allocated = 325.3 GB
  thread = "worker-thread-1" (javaThreadId = 141)
}
```

**Key fields**: `allocated`, `thread`

### jdk.JavaMonitorEnter
Thread blocked waiting to acquire a `synchronized` monitor.

```
jdk.JavaMonitorEnter {
  startTime = ...
  duration = 35.00 ms
  monitorClass = java.util.HashMap (classLoader = bootstrap)
  previousOwner = "other-thread" (javaThreadId = 99)
  eventThread = "worker-1" (javaThreadId = 42)
}
```

**Key fields**: `duration` (ms), `monitorClass`, `eventThread`

### jdk.ThreadPark
Thread parked via `LockSupport.park()`, covering `ReentrantLock`, `CountDownLatch`, etc.

```
jdk.ThreadPark {
  startTime = ...
  duration = 12.00 ms
  parkedClass = java.util.concurrent.locks.AbstractQueuedSynchronizer (classLoader = bootstrap)
  eventThread = "worker-2" (javaThreadId = 55)
}
```

**Key fields**: `duration` (ms), `parkedClass`, `eventThread`

### jdk.FileRead / jdk.FileWrite
File I/O operation.

```
jdk.FileRead {
  startTime = ...
  duration = 5.00 ms
  path = "/data/app/config.properties"
  bytesRead = 4096
  eventThread = "main" (javaThreadId = 1)
}
```

**Key fields**: `duration` (ms), `path`, `bytesRead` / `bytesWritten`

### jdk.SocketRead / jdk.SocketWrite
Network socket I/O operation.

```
jdk.SocketRead {
  startTime = ...
  duration = 25.00 ms
  host = "db.internal"
  port = 5432
  bytesRead = 1024
  eventThread = "http-handler-3" (javaThreadId = 77)
}
```

**Key fields**: `duration` (ms), `host`, `port`, `bytesRead` / `bytesWritten`

## Stack Trace Format

Stack frames in JFR text exports follow this format:

```
    fully.qualified.ClassName.methodName(ArgType1, ArgType2) line: N
```

- Truncated stacks end with `...`
- Lambda methods appear as `ClassName.lambda$outerMethod$N()`
- Inner classes: `OuterClass$InnerClass.method()`

## Weight vs allocationSize

- `weight` (ObjectAllocationSample): Sampled estimate. Actual allocation = weight × sampling interval factor. Use for relative comparison, not absolute totals.
- `allocationSize` (ObjectAllocationOutsideTLAB): Exact size in bytes for large allocations.
