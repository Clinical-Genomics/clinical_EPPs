#!/home/glsai/miniconda2/envs/epp_master/bin/python
DESC="""EPP script to calculate sample volume and EB volume from concentration and volume
udf:s in Clarity LIMS.
Maya Brandi
"""
from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD

from genologics.entities import Process
import sys

class BufferVolume():
    def __init__(self, process):
        self.process = process
        self.artifacts = []
        self.passed_arts = 0
        self.failed_arts = 0
        self.missing_udfs = False
        self.high_concentration = False
        self.final_concentration = 2

    def get_artifacts(self):
        all_artifacts = self.process.all_outputs(unique=True)
        self.artifacts = filter(lambda a: a.output_type == "Analyte", all_artifacts)

    def apply_calculations(self):
        for artifact in self.artifacts:
            concentration = artifact.udf.get('Concentration')
            artifact.qc_flag = 'PASSED'
            if concentration is None:
                self.missing_udfs = True
                self.failed_arts +=1
                continue
            if artifact.samples[0].name[0:6] == 'NTC-CG':
                buffer_volume = 15
                samp_vol = 0
            elif concentration < 2:
                samp_vol = 15
                buffer_volume = 0
                total_volume = buffer_volume + samp_vol
            elif 2 <= concentration <= 7.5:
                total_volume = 15
                samp_vol = float(self.final_concentration * total_volume )/concentration
                buffer_volume = total_volume - samp_vol
                if buffer_volume < 2:
                    samp_vol = 15
                    buffer_volume = 0
            elif 7.5 < concentration <= 60:
                samp_vol = 4
                total_volume = float(concentration * samp_vol)/self.final_concentration
                buffer_volume = total_volume - samp_vol
            else:
                artifact.qc_flag = 'FAILED'
                self.high_concentration = True
                continue
            self.passed_arts +=1
            artifact.udf['Total Volume (uL)'] = buffer_volume + samp_vol
            artifact.udf['Volume Buffer (ul)'] = buffer_volume
            artifact.udf['Sample Volume (ul)'] = samp_vol
            artifact.put()

def main(lims,args):
    process = Process(lims,id = args.pid)
    BV = BufferVolume(process)
    BV.get_artifacts()
    BV.apply_calculations()

    d = {'ca': BV.passed_arts,
         'ia': BV.failed_arts}

    abstract = ("Updated {ca} artifact(s), skipped {ia} artifact(s) with "
                "wrong and/or blank values for some udfs. ").format(**d)

    if BV.missing_udfs:
        sys.exit('Could not apply calculations for all samples. "Concentration" must be set.')
    elif BV.high_concentration:
        sys.exit('Concentration high for some samples. ' + abstract)
    elif BV.failed_arts:
        sys.exit(abstract)
    else:
        print >> sys.stderr, abstract


if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('--pid',
                        help='Lims id for current Process')
    args = parser.parse_args()

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()

    main(lims, args)

