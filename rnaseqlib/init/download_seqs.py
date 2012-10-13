##
## Downloading of genomic sequences related to pipeline
## 

# Basic Downloading
#
# efetch.fcgi?db=<database>&id=<uid_list>&rettype=<retrieval_type>
# &retmode=<retrieval_mode>
#
# Input: List of UIDs (&id); Entrez database (&db); Retrieval type (&rettype); Retrieval mode (&retmode)
# Output: Formatted data records as specified
# Example: Download nuccore GIs 34577062 and 24475906 in FASTA format
# http://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=nuccore&id=34577062,24475906&rettype=fasta&retmode=text

import os
import sys
import time

import rnaseqlib
import rnaseqlib.utils as utils
import rnaseqlib.cluster_utils.cluster as cluster
import rnaseqlib.fasta_utils as fasta_utils

from rnaseqlib.init.genome_urls import *
import rnaseqlib.init.download_utils as download_utils


##
## Mapping from organisms to misc. sequence NCBI
## accession IDs.
##
NCBI_MISC_SEQS = {"human": {"chrRibo": "U13369.1",
                            "chrMito": None},
                  "mouse": {"chrRibo": "BK000964.1",
                            "chrMito": None}}

def download_ncbi_fasta(access_id, output_dir):
    """
    Download NCBI FASTA file by accession number and
    label them as access.fasta in the given output directory.
    """
    ncbi_url = "http://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=nuccore&id=%s&rettype=fasta&retmode=text" \
        %(access_id)
    url_filename = download_utils.download_url(ncbi_url,
                                               output_dir,
                                               basename="%s.fa" %(access_id),
                                               binary=False)
    return url_filename
    

def download_genome_seq(genome,
                        output_dir):
    """
    Download genome sequence files from UCSC.
    """
    print "Downloading genome sequence files for %s" %(genome)
    print "  - Output dir: %s" %(output_dir)
    output_dir = os.path.join(output_dir, "genome")
    if os.path.isdir(output_dir):
        print "Directory %s exists; skipping downloading of genome." \
            %(output_dir)
        return None
    utils.make_dir(output_dir)
    # Change to output directory
    os.chdir(output_dir)
    ##
    ## Download the genome sequence files
    ##
    genome_url = "%s/%s/chromosomes/" %(UCSC_GOLDENPATH,
                                        genome)
    # Fetch all chromosome sequence files
    print "Downloading genome files from: %s" %(genome_url)
    download_utils.wget(download_cmd)
    print "Downloading took %.2f minutes" %((t2 - t1)/60.)
    ##
    ## Uncompress the files
    ##
    print "Uncompressing files..."
    uncompress_cmd = "gunzip %s/*.gz" %(output_dir)
    t1 = time.time()
    os.system(uncompress_cmd)
    t2 = time.time()
    print "Uncompressing took %.2f minutes" %((t2 - t1)/60.)
    

def download_misc_seqs(genome, output_dir):
    """
    Download assorted sequences related to genome.
    """
    # Mapping from sequence label (e.g. rRNA)
    # to accession numbers
    organism = None
    if genome.startswith("hg"):
        organism = "human"
    elif genome.startswith("mm"):
        organism = "mouse"
    else:
        print "Error: Unsupported genome."
        sys.exit(1)
    # Fetch the accession numbers for the organism's
    # misc sequences and download them
    misc_seqs = NCBI_MISC_SEQS[organism]
    ncbi_outdir = os.path.join(output_dir, "ncbi")
    utils.make_dir(ncbi_outdir)
    for seq_label, access_id in misc_seqs.iteritems():
        if access_id is None:
            continue
        print "Downloading: %s (NCBI: %s)" %(seq_label,
                                             access_id)
        url_filename = download_ncbi_fasta(access_id, ncbi_outdir)
        fasta_in = fasta_utils.fasta_read(url_filename)
        output_filename = os.path.join(ncbi_outdir, "%s.fa" %(seq_label))
        fasta_out = open(output_filename, "w")
        print "  - Writing to: %s" %(output_filename)
        # Fetch first FASTA record
        rec = fasta_in[0]
        curr_label, fasta_seq = rec.header, rec.seq
        # Output it with the required label
        new_rec = (">%s" %(seq_label), fasta_seq)
        fasta_utils.write_fasta(fasta_out, [new_rec])
