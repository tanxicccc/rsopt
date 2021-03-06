from rsopt.configuration import Options


class Configuration:
    def __init__(self):
        self.jobs = []
        self._options = Options()

    @property
    def options(self):
        return self._options

    # TODO: rename to get_job_parameters same for settings and setup
    def parameters(self, job=0):
        assert self.jobs[job], f"Requested job: {job} is not registered in the Configuration"

        return self.jobs[job].parameters

    def settings(self, job=0):
        assert self.jobs[job], f"Requested job: {job} is not registered in the Configuration"

        return self.jobs[job].settings

    def setup(self, job=0):
        assert self.jobs[job], f"Requested job: {job} is not registered in the Configuration"

        return self.jobs[job].setup

    @options.setter
    def options(self, options):
        new_options = self._options.get_option(options)()
        for name, value in options.items():
            new_options.parse(name, value)
        self._options = new_options

    @property
    def method(self):
        return self._options.method

    def set_jobs(self, jobs):
        if hasattr(jobs, '__iter__'):
            self.jobs.extend(jobs)
        else:
            self.jobs.append(jobs)

    def get_dimension(self):
        dim = 0
        for job in self.jobs:
            dim += len(job.parameters)

        return dim

    def get_parameters_list(self, attribute, formatter=list):
        # get list attribute from all job parameters and return based on formatter
        attribute_list = []
        for job in self.jobs:
            attribute_list.extend(job._parameters.__getattribute__(attribute)())

        return formatter(attribute_list)