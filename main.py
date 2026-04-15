import json

from documentcloud.addon import AddOn


class DetectOCRErrors(AddOn):
    """Detect OCR Errors on forms for AE docs"""

    def main(self):

        # User agent
        self.client.session.headers.update(
            {"User-Agent": "Disclose AE Detect OCR Errors Add-On"}
        )

        # Inputs
        project_id = self.data.get("project")

        fix_errors = self.data.get("fix_errors")
        fix_max_pages = self.data.get("fix_max_pages")
        fix_only_if_no_depts = self.data.get("fix_only_if_no_depts")

        # Load known errors
        with open("first_page_errors.json", "r") as file:
            known_errors = json.load(file)

        for document in self.get_documents():

            if project_id in document.projects:

                first_page_text = document.get_page_text(1)
                if first_page_text in known_errors:
                    document.data["form_error"] = "yes"
                    document.save()

                    if fix_errors:

                        if document.pages <= fix_max_pages or fix_max_pages == 0:

                            if (
                                fix_only_if_no_depts == False
                                or "departments" not in document.data
                            ):

                                self.client.post(
                                    "addon_runs/",
                                    json={
                                        "addon": 544,
                                        "parameters": {"to_tag": True},
                                        "documents": [document.id],
                                        "dismissed": True,
                                    },
                                )
                else:
                    document.data["form_error"] = "no"
                    document.save()


if __name__ == "__main__":
    DetectOCRErrors().main()
