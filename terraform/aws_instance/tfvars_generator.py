import os

from jinja2 import Template


class TFVarGenerator:

    def __init__(self):
        try:
            self.inject_data = {
                "instance_type": os.environ['INSTANCE_TYPE'].strip("\n\t "),
                "image_id": os.environ['IMAGE_ID'].strip("\n\t "),
                "tags": {
                    "Name": os.environ['TAG_NAME'].strip("\n\t ")
                },
            }
        except Exception as err:
            raise Exception(err)

    def create_tfvars_file(self):
        """
        This method create tfvars file in the current working directory
        :return:
        """
        file_name = "input_vars.tfvars"
        with open(file_name, 'w') as tfvars_file:
            tfvars_file.write(self.__inject_data_to_template())

    def __inject_data_to_template(self):
        """
        This method inject the data into the template
        :return:
        """
        template_path = "input_tfvars_template"
        with open(template_path) as file:
            template = Template(file.read())
            return template.render(self.inject_data)


tfvars_generator = TFVarGenerator()
tfvars_generator.create_tfvars_file()
