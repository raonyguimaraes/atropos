import sys

DEFAULT_ADAPTERS = [
    "AGATCGGAAGAGCACACGTCTGAACTCCAGTCACACAGTGATCTCGTATGCCGTCTTCTGCTTG",
    "AGATCGGAAGAGCGTCGTGTAGGGAAAGAGTGTAGATCTCGGTGGTCGCCGTATCATT"
]

class fileoutput(object):
    def __init__(self, path, mode='wt'):
        self.close = False
        if path == '-':
            self.fh = sys.stdout
        else:
            self.fh = open(path, mode)
            self.close = True
    
    def __enter__(self):
        return self.fh
    
    def __exit__(self, type, value, traceback):
        if self.close:
            self.fh.close()

def fq_iterator(i, mate=None):
    for read in zip(*[i] * 4):
        name = read[0].rstrip()[1:]
        if mate is None:
            mate = name[-1]
            name = name[:-2]
        yield (name, mate, read[1].rstrip(), read[3].rstrip())

def aln_iterator(i):
    for line in i:
        if line[0] in ('@','#'):
            continue
        assert line[0] == '>'
        chrm, name, pos, strand = line[1:].rstrip().split('\t')
        if name.endswith('-1'):
            name = name[:-2]
        mate = name[-1]
        name = name[:-2]
        ref = next(i).rstrip()
        actual = next(i).rstrip()
        yield (name, mate, chrm, pos, strand, ref, actual)

def find_best_alignment(ref, query, side, min_match=1, cache=None, start=0, end=0.4, inc=0.01):
    from atropos import align
    best_match = None
    best_alternate = None
    
    for err in seq(start, end, inc):
        if cache is not None and err in cache:
            aligner = cache[err]
        else:
            aligner = make_aligner(ref, err, side)
            if cache is not None:
                cache[err] = aligner
        match = aligner.locate(query)
        if match is not None:
            ref_match = match[1] - match[0]
            if ref_match >= min_match:
                if match[5] == 0:
                    return match
                elif best_match is None or match[5] < best_match[5]:
                    best_match = match
            elif (best_alternate is None or ref_match > (best_alternate[1] - best_alternate[0]) or
                        (ref_match == (best_alternate[1] - best_alternate[0]) and match[5] < best_alternate[5])):
                best_alternate = match
    
    if best_match is not None:
        return best_match
    else:
        return best_alternate

def seq(start, end, inc):
    i = start
    while i <= end:
        yield i
        i += inc

def enumerate_range(collection, start, end):
    'Generates an indexed series:  (0,coll[0]), (1,coll[1]) ...'
    i = start
    it = iter(collection)
    while i < end:
        yield (i, next(it))
        i += 1

class BAMReader(object):
    """Reads read pairs from a name-sorted bam file."""
    def __init__(self, bam_file):
        import pysam
        self.bam = iter(pysam.AlignmentFile(bam_file, "rb"))
        self.cached = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, type, value, traceback):
        self.bam.close()
            
    def __iter__(self):
        return self
    
    def __next__(self):
        read = self.cached or next(self.bam)
        name = read.query_name
            
        r1 = []
        r2 = []
        def add_read(read):
            if read.is_read1:
                r1.append(read)
            else:
                r2.append(read)
            
        add_read(read)
        peek = next(self.bam)
        while peek.query_name == name:
            add_read(peek)
            peek = next(self.bam)
        self.cached = peek
        
        return (name, r1, r2)
