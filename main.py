import json

from documentcloud.addon import AddOn


class DetectOCRErrors(AddOn):
    """An example Add-On for DocumentCloud."""

    def main(self):
        """The main add-on functionality goes here."""

        project_id = self.data.get("project")

        # Load known errors
        with open("first_page_errors.json", "r") as file:
            known_errors = json.load(file)

        for document in self.get_documents():

            if project_id in document.projects:

                first_page_text = document.get_page_text(1)
                if first_page_text in known_errors:
                    document.data["form_error"] = "yes"
                    document.save()
                else:
                    document.data["form_error"] = "no"
                    document.save()


if __name__ == "__main__":
    DetectOCRErrors().main()
