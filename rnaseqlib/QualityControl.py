import os
import sys
import time

import rnaseqlib
import rnaseqlib.fastq_utils as fastq_utils
import rnaseqlib.utils as utils

import pandas
import pysam

from collections import defaultdict


class QualityControl:
    """ 
    Quality control object. Defined for
    RNA-Seq sample.
    """
    def __init__(self, sample, pipeline):
        # Pipeline instance that the sample is attached to
        self.pipeline = pipeline
        self.sample = sample
        self.settings_info = pipeline.settings_info
        # QC filename for sample
        self.qc_filename = None
        # QC header: order of QC fields to be outputted
        self.qc_header = []
        # QC results
        self.qc_results = {}
        # QC output dir
        self.qc_outdir = self.pipeline.pipeline_outdirs["qc"]
        # Number of reads (in fastq file)        
        self.num_reads = None
        # Number of mapped reads
        self.num_mapped = None
        # Number of ribosomal reads per sample
        self.num_ribo = None
        # Number of mitochondrial reads per sample
        self.num_mito = None
        # Number of intronic reads per sample
        self.num_intronic = None
        # Number of intergenic reads per sample
        self.num_intergenic = None


    def get_num_reads(self):
        """
        Return number of reads in FASTQ file.
        """
        fastq_entries = fastq_utils.get_fastq_entries(self.sample.reads_filename)
        num_reads = 0
        for entry in fastq_entries:
            num_reads += 1
        self.num_reads = num_reads
        return self.num_reads
    

    def get_num_mapped(self):
        """
        Get number of mapped reads, not counting duplicates, i.e.
        reads that have alignments in the BAM file.
        """
        bam_read_ids = {}
        bamfile = pysam.Samfile(self.sample.bam_filename, "rb")
        for read in bamfile:
            # Do not count duplicates twice
            bam_read_ids[read.qname] = 1
        self.num_mapped = len(bam_read_ids.keys())
        return self.num_mapped
    

    def get_exon_intergenic_ratio(self):
        pass
    

    def get_exon_intron_ratio(self):
        pass
    

    def get_num_ribo(self, chr_ribo="chrRibo"):
        """
        Compute the number of ribosomal mapping reads per
        sample.

        - chr_ribo denotes the name of the ribosome containing
          chromosome.
        """
        bamfile = pysam.Samfile(self.sample.bam_filename, "rb")
        # Retrieve all reads on the ribo chromosome
        ribo_reads = bamfile.fetch(reference=chr_ribo,
                                   start=None,
                                   end=None)
        num_ribo = 0
        # Count reads (fetch returns an iterator)
        for r in ribo_reads:
            num_ribo += 1
        return num_ribo


    def get_qc(self):
        return self.qc_results
        

    def compute_qc(self):
        """
        Compute all QC metrics for sample.
        """
        self.num_reads = self.get_num_reads()
        self.num_mapped = self.get_num_mapped()
        self.num_ribo = self.get_num_ribo()
        ##
        ## Header that specifies order of QC fields to be outputted
        ##
        self.qc_header = ["num_reads", 
                          "num_mapped",
                          "num_ribo"]
        self.qc_results["num_reads"] = self.num_reads
        self.qc_results["num_mapped"] = self.num_mapped
        self.qc_results["num_ribo"] = self.num_ribo
        return self.qc_results
        
        
    def output_qc(self):
        """
        Output QC metrics for sample.
        """
        sample_outdir = os.path.join(self.qc_outdir,
                                     self.sample.label)
        utils.make_dir(sample_outdir)
        self.qc_filename = os.path.join(sample_outdir,
                                        "%s.qc.txt" %(self.sample.label))
        if os.path.isfile(self.qc_filename):
            print "SKIPPING %s, since %s already exists..." %(self.sample.label,
                                                              qc_filename)
            return None
        # Header for QC output file for sample
        qc_headers = ["num_reads", "num_mapped", "num_ribo"]
        qc_entry = {"num_reads": self.num_reads,
                    "num_mapped": self.num_mapped,
                    "num_ribo": self.num_ribo}
        qc_df = pandas.DataFrame([qc_entry])
        # Write QC information as csv
        qc_df.to_csv(self.qc_filename,
                     cols=qc_headers,
                     sep="\t",
                     index=False)
        

    def get_seq_cycle_profile(self, fastq_filename,
                              first_n_seqs=None):#sample):
        """
        Compute the average 'N' bases (unable to sequence)
        as a function of the position of the read.
        """
        fastq_file = fastq_utils.read_open_fastq(fastq_filename)
        fastq_entries = fastq_utils.read_fastq(fastq_file)
        # Mapping from position in read to number of Ns
        num_n_bases = defaultdict(int)
        # Mapping from position in read to total number of
        # reads in that position
        num_reads = defaultdict(int)
        num_entries = 0
        print "Computing sequence cycle profile for: %s" %(fastq_filename)
        if first_n_seqs != None:
            print "Looking at first %d sequences only" %(first_n_seqs)
        for entry in fastq_entries:
            if first_n_seqs != None:
                # Stop at requested number of entries if asked to
                if num_entries >= first_n_seqs:
                    break
            header1, seq, header2, qual = entry
            seq_len = len(seq)
            for n in range(seq_len):
                if seq[n] == "N":
                    # Record occurrences of N
                    num_n_bases[n] += 1
                num_reads[n] += 1
            num_entries += 1
        # Compute percentage of N along each position
        percent_n = []
        for base_pos in range(max(num_reads.keys())):
            curr_percent_n = float(num_n_bases[base_pos]) / num_reads[base_pos]
            percent_n.append(curr_percent_n)
        return percent_n

        
class QCStats:
    """
    Represntation of QC stats for a set of samples.
    """
    def __init__(self, samples):
        self.samples = samples
        self.qc_stats = []


    def output_qc(self, output_filename):
        """
        Output QC to file.
        """
        print "Outputting QC information for all samples..."
        self.compile_qc(self.samples)
        self.to_csv(output_filename)


    def compile_qc(self, samples,
                   sample_header="sample"):
        """
        Combined the QC output of a given set of samples
        into one object.
        """
        if len(samples) == 0:
            print "Error: No samples given to compile QC from!"
            sys.exit(1)
        # Fetch QC header of first sample. Add to its
        # beginning a field for the sample name
        qc_header = [sample_header] + samples[0].qc_header
        for sample in samples:
            # Record sample name
            qc_entry[sample_header] = sample.label
            # Copy its QC results
            qc_entry = sample.qc_results.copy()
            self.qc_stats.append(qc_entry)
        self.qc_stats = pandas.DataFrame(qc_stats)
        return self.qc_stats
    

    def to_csv(self, output_filename):
        self.qc_stats.to_csv(output_filename,
                             sep="\t",
                             index=False)
