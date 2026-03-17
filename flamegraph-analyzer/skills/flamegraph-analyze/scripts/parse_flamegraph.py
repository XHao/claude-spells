#!/usr/bin/env python3
"""
Parse async-profiler HTML flamegraph and extract frame data.

Outputs JSON with:
  - title: flamegraph title
  - total_samples: total sample count
  - detected_frameworks: list of framework category keys found (sorted by sample count)
  - frames: [{name, samples, pct}] sorted by samples desc
  - categories: {cat: {samples, pct}}
  - top_per_category: {cat: [{name, samples, pct}]}
"""

import re
import sys
import json
from collections import defaultdict


def decode_cpool(content):
    """Decode async-profiler delta-compressed cpool string pool."""
    m = re.search(r'const cpool = \[(.*?)\];', content, re.DOTALL)
    if not m:
        return []
    raw_entries = re.findall(r"'((?:[^'\\]|\\.)*)'", m.group(1))
    if not raw_entries:
        return []

    # First entry is literal (no delta encoding)
    cpool = [raw_entries[0]]
    for i in range(1, len(raw_entries)):
        e = raw_entries[i]
        if not e:
            cpool.append('')
            continue
        # charCode(first_char) - 32 = number of chars to keep from previous string
        shared = ord(e[0]) - 32
        suffix = e[1:]
        full = (cpool[-1][:shared] if shared > 0 else '') + suffix
        cpool.append(full)
    return cpool


def parse_frames(content, cpool):
    """Parse f/u/n data calls and accumulate sample counts per frame."""
    cpool_end_idx = content.find('];', content.find('const cpool = [')) + 2
    data_start = content.find('unpack(cpool);', cpool_end_idx)
    if data_start == -1:
        data_start = cpool_end_idx
    data_end = content.find('</script>', data_start)
    data_section = content[data_start:data_end]

    frame_samples = defaultdict(int)
    # f(key, level, left, width, ...) | u(key, width, ...) | n(key, width, ...)
    calls = re.findall(r'([fun])\((\d+)(?:,(\d+))?(?:,(\d+))?', data_section)

    for call in calls:
        func, key_s, arg2, arg3 = call
        key = int(key_s)
        cpool_idx = key >> 3  # key >>> 3 in JS

        if func == 'f':
            width = int(arg3) if arg3 else 0
        else:
            width = int(arg2) if arg2 else 0

        if cpool_idx < len(cpool) and width > 0:
            frame_samples[cpool[cpool_idx]] += width

    return frame_samples


# Framework registry — ordered, more-specific entries must come before less-specific ones.
# Each entry: (category_key, display_label, [package_prefixes_lowercase])
# The catch-all entries (third_party_java) MUST be last.
FRAMEWORK_REGISTRY = [
    ('elasticsearch',  'Elasticsearch',           ['org/elasticsearch', 'org/elastic/']),
    ('lucene',         'Lucene',                  ['org/apache/lucene']),
    ('netty',          'Netty',                   ['io/netty']),
    ('spring',         'Spring',                  ['org/springframework', 'org/spring']),
    ('kafka',          'Kafka',                   ['org/apache/kafka', 'kafka/']),
    ('grpc',           'gRPC',                    ['io/grpc']),
    ('flink',          'Apache Flink',            ['org/apache/flink']),
    ('spark',          'Apache Spark',            ['org/apache/spark']),
    ('hadoop',         'Hadoop',                  ['org/apache/hadoop']),
    ('hbase',          'HBase',                   ['org/apache/hbase']),
    ('zookeeper',      'ZooKeeper',               ['org/apache/zookeeper']),
    ('jackson',        'Jackson',                 ['com/fasterxml/jackson']),
    ('guava',          'Guava',                   ['com/google/common', 'com/google/guava']),
    ('protobuf',       'Protobuf',                ['com/google/protobuf']),
    ('slf4j_logback',  'Logging (SLF4J/Logback)', ['org/slf4j', 'ch/qos/logback']),
    ('log4j',          'Log4j',                   ['org/apache/log4j', 'org/apache/logging']),
    ('hibernate',      'Hibernate / JPA',         ['org/hibernate']),
    ('rxjava',         'RxJava / Reactor',        ['rx/', 'reactor/']),
    # Catch-alls — must come LAST so specific entries above match first
    ('third_party_java', 'Third-party Java',      ['com/google', 'org/apache/']),
]

# Derived from the registry — no dual-maintenance needed
CATEGORY_LABELS = {key: label for key, label, _ in FRAMEWORK_REGISTRY}
CATEGORY_LABELS.update({
    'jdk':          'JDK / Java stdlib',
    'jvm_internal': 'JVM internal (C++)',
    'kernel':       'Kernel / interrupt',
    'native_lib':   'Native library',
    'app_java':     'App Java',
    'other':        'Other',
})

# Categories that represent JVM infrastructure, not detected frameworks
_TIER1_CATS = frozenset({'jdk', 'jvm_internal', 'kernel', 'native_lib', 'app_java', 'other'})


def categorize_frame(name):
    """Categorize a frame name into a high-level category.

    Three tiers:
      1. JVM infrastructure — determined by structural properties of the frame name
      2. Known frameworks   — detected via FRAMEWORK_REGISTRY prefix matching
      3. App Java / other   — residual
    """
    n = name.lower()

    # Tier 1: JVM infrastructure (structural rules, always checked first)
    if 'java/' in n or 'javax/' in n or 'sun/' in n or 'jdk/' in n or 'com/sun/' in n:
        return 'jdk'
    if '::' in name and not name.startswith('/'):
        return 'jvm_internal'
    if name.startswith('asm_') or 'interrupt' in n or 'syscall' in n:
        return 'kernel'
    if name.startswith('/') or '.so' in name or name.endswith('@plt'):
        return 'native_lib'

    # Tier 2: framework detection (registry-driven, prefix match)
    for key, _, prefixes in FRAMEWORK_REGISTRY:
        for prefix in prefixes:
            if prefix in n:
                return key

    # Tier 3: app code
    if '/' in name and name[0].islower():
        return 'app_java'
    return 'other'


def analyze(html_path):
    content = open(html_path, encoding='utf-8', errors='replace').read()

    # Title
    title_m = re.search(r'<h1>(.*?)</h1>', content)
    title = title_m.group(1) if title_m else 'Flamegraph'

    # Detect profiler type
    profiler = 'async-profiler' if 'async-profiler' in content else 'unknown'

    cpool = decode_cpool(content)
    frame_samples = parse_frames(content, cpool)

    # Remove the synthetic "all" root frame from per-frame stats
    frame_samples.pop('all', None)

    total = sum(frame_samples.values())

    sorted_frames = sorted(frame_samples.items(), key=lambda x: x[1], reverse=True)

    # Build per-frame list (top 200)
    frames = []
    for name, count in sorted_frames[:200]:
        frames.append({
            'name': name,
            'samples': count,
            'pct': round(100 * count / total, 2) if total else 0,
            'category': categorize_frame(name),
        })

    # Category aggregation
    cat_samples = defaultdict(int)
    for name, count in sorted_frames:
        cat_samples[categorize_frame(name)] += count

    categories = {}
    for cat, count in sorted(cat_samples.items(), key=lambda x: x[1], reverse=True):
        categories[cat] = {
            'label': CATEGORY_LABELS.get(cat, cat),
            'samples': count,
            'pct': round(100 * count / total, 2) if total else 0,
        }

    # Detected frameworks: non-Tier-1 categories, sorted by sample count descending
    detected_frameworks = sorted(
        [cat for cat in cat_samples if cat not in _TIER1_CATS],
        key=lambda c: cat_samples[c],
        reverse=True,
    )

    # Top 10 frames per category
    top_per_cat = defaultdict(list)
    for name, count in sorted_frames:
        cat = categorize_frame(name)
        if len(top_per_cat[cat]) < 10:
            top_per_cat[cat].append({
                'name': name,
                'samples': count,
                'pct': round(100 * count / total, 2) if total else 0,
            })

    return {
        'title': title,
        'profiler': profiler,
        'total_samples': total,
        'unique_frames': len(frame_samples),
        'detected_frameworks': detected_frameworks,
        'frames': frames,
        'categories': categories,
        'top_per_category': dict(top_per_cat),
    }


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: parse_flamegraph.py <flamegraph.html>', file=sys.stderr)
        sys.exit(1)
    result = analyze(sys.argv[1])
    print(json.dumps(result, ensure_ascii=False, indent=2))
