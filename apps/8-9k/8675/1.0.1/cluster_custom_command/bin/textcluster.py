#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import difflib
import logging
import os

# -----------------------------------------------------
# FORCE LOG FILE CREATION (EARLY)
# -----------------------------------------------------
LOG_PATH = '/opt/Splunk/var/log/splunk/textcluster.log'

try:
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write("---- textcluster starting ----\n")
except Exception as e:
    print("LOG INIT ERROR:", e, file=sys.stderr)

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(message)s'
)

logging.debug("textcluster.py loaded successfully.")

# Splunk imports must come after logging
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option


@Configuration()
class TextClusterCommand(StreamingCommand):

    field = Option(require=True, doc="Field containing text to cluster")
    threshold = Option(require=False, default=0.35, doc="Distance threshold (0–1).")

    # -----------------------------------------------------
    # Similarity score
    # -----------------------------------------------------
    def sim(self, a, b):
        try:
            return difflib.SequenceMatcher(None, a, b).ratio()
        except Exception as e:
            logging.error("Similarity error: %s", e)
            return 0.0

    # -----------------------------------------------------
    # Best common substring (equivalent to sklearn prefix grouping)
    # -----------------------------------------------------
    def best_common_substring(self, strings):
        if not strings:
            return ""

        base = strings[0]
        best = ""

        for s in strings[1:]:
            seq = difflib.SequenceMatcher(None, base, s)
            match = seq.find_longest_match(0, len(base), 0, len(s))
            if match.size > len(best):
                best = base[match.a: match.a + match.size]

        return best.strip()

    # -----------------------------------------------------
    # Pure Python Hierarchical Clustering (average linkage)
    # Replicates sklearn AgglomerativeClustering(affinity="precomputed", linkage="average")
    # -----------------------------------------------------
    def hierarchical_clustering(self, strings, threshold):

        n = len(strings)
        clusters = [[i] for i in range(n)]  # each item starts in its own cluster

        # Precompute similarity matrix
        sim = [[self.sim(strings[i], strings[j]) for j in range(n)] for i in range(n)]

        # Convert to distance matrix (1 - similarity)
        dist = [[1 - sim[i][j] for j in range(n)] for i in range(n)]

        # Average linkage distance between clusters
        def cluster_distance(c1, c2):
            d = 0
            count = 0
            for i in c1:
                for j in c2:
                    d += dist[i][j]
                    count += 1
            return d / count

        merged = True
        while merged:
            merged = False
            best_pair = None
            best_distance = threshold  # merge only if distance < threshold

            # Find lowest inter-cluster distance
            for i in range(len(clusters)):
                for j in range(i + 1, len(clusters)):
                    d = cluster_distance(clusters[i], clusters[j])
                    if d < best_distance:
                        best_distance = d
                        best_pair = (i, j)

            # Merge if below threshold
            if best_pair:
                i, j = best_pair
                clusters[i] += clusters[j]
                del clusters[j]
                merged = True

        # Convert cluster lists to assignment array
        assignment = [None] * n
        for cid, members in enumerate(clusters):
            for idx in members:
                assignment[idx] = cid

        return assignment

    # -----------------------------------------------------
    # STREAM EXECUTION
    # -----------------------------------------------------
    def stream(self, events):
        logging.debug("Entered stream()")

        try:
            events = list(events)
            if not events:
                logging.debug("No events received")
                return

            texts = []
            for e in events:
                val = e.get(self.field, "")
                if val is None:
                    val = ""
                texts.append(str(val).lower())

            logging.debug("Input texts: %s", texts)

            threshold = float(self.threshold)

            # 1. Perform clustering
            cluster_ids = self.hierarchical_clustering(texts, threshold)
            logging.debug("Cluster assignments: %s", cluster_ids)

            # 2. Group items by cluster
            cluster_groups = {}
            for idx, cid in enumerate(cluster_ids):
                cluster_groups.setdefault(cid, []).append(texts[idx])

            logging.debug("Cluster groups: %s", cluster_groups)

            # 3. Extract best matching pattern for each cluster
            patterns = {
                cid: self.best_common_substring(group)
                for cid, group in cluster_groups.items()
            }

            logging.debug("Cluster patterns: %s", patterns)

            # 4. Output enriched events
            for idx, event in enumerate(events):
                cid = cluster_ids[idx]
                patt = patterns.get(cid, "")
                score = self.sim(patt, texts[idx]) if patt else 0.0

                event["cluster_id"] = cid
                event["matching_pattern"] = patt
                event["similarity_score"] = round(score, 3)

                logging.debug("OUTPUT EVENT: cid=%s pattern='%s' score=%s",
                              cid, patt, score)

                yield event

        except Exception as e:
            logging.error("FATAL ERROR in stream(): %s", e, exc_info=True)
            raise e


# -----------------------------------------------------
# Dispatch the command
# -----------------------------------------------------
dispatch(TextClusterCommand, sys.argv, sys.stdin, sys.stdout)

