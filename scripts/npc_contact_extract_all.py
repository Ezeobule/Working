#!/usr/bin/env python3
import npc_nationwide_extract as nationwide

nationwide.extractor.OUTDIR = "npc_output"
nationwide.extractor.TARGET = 10000
nationwide.extractor.main()
