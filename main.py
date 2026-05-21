import json
import sys
from datetime import datetime, timedelta

from documentcloud.addon import AddOn
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError


class DetectOCRErrors(AddOn):
    """Detect OCR Errors on forms for AE docs"""

    def check_time_limit(self):
        if datetime.now() - self.start_time > timedelta(minutes=self.time_limit):
            print("Time limit exceeded. Stopping add-on...")
            print(f"Processed {self.processed_count} documents")
            sys.exit(0)

    def save_document(self, document):
        if self.dry_run:
            print(f"[dry_run] would save document {document.id}")
            return

        @retry(
            stop=stop_after_attempt(5),
            wait=wait_exponential(multiplier=1, min=1, max=30),
        )
        def save():
            document.save()

        try:
            save()
        except RetryError:
            print(f"closed due to exceeded max_retries on document {document.id}")
            sys.exit(1)

    def send_to_reprocessing(self, document):
        if self.dry_run:
            print(
                f"[dry_run] would send document {document.id} to Azure OCR reprocessing"
            )
            return

        self.client.post(
            "addon_runs/",
            json={
                "addon": 544,
                "parameters": {"to_tag": True},
                "documents": [document.id],
                "dismissed": True,
            },
        )

    def main(self):

        # User agent
        self.client.session.headers.update(
            {"User-Agent": "Disclose AE Detect OCR Errors Add-On"}
        )

        # Inputs
        project_id = self.data.get("project")

        fix_errors = self.data.get("fix_errors")
        fix_max_pages = self.data.get("fix_max_pages")

        self.dry_run = self.data.get("dry_run")

        self.time_limit = self.data.get("time_limit")
        self.start_time = datetime.now()
        self.processed_count = 0

        # Load known errors
        with open("first_page_errors.json", "r") as file:
            known_errors = json.load(file)

        results = self.client.documents.search(
            f"project:{project_id} status:success -data_ocr_form_problem:*"
        )

        for document in results:

            self.check_time_limit()

            # if the doc has form_error:yes
            if (
                "form_error" in document.data
                and document.data["form_error"][0] == "yes"
            ):
                #  we retag to ocr_form_problem:true
                document.data["ocr_form_problem"] = "true"

                # remove the form_error metadata
                del document.data["form_error"]

                # and save
                self.save_document(document)

            # if not (the doc has form_error:no or  # if the doc has no form_error key in its metadata)
            else:
                first_page_text = document.get_page_text(1)

                # Check if the first page is in errors
                if first_page_text in known_errors:
                    document.data["ocr_form_problem"] = "true"
                    to_reprocess = True
                    print(f"Document {document.id} marked for reprocessing")
                else:
                    document.data["ocr_form_problem"] = "false"
                    to_reprocess = False

                document.data.pop("form_error", None)

                self.save_document(document)

                if to_reprocess and fix_errors:

                    if document.pages <= fix_max_pages or fix_max_pages == 0:

                        self.send_to_reprocessing(document)

            self.processed_count += 1

        print(f"Processed {self.processed_count} documents")


if __name__ == "__main__":
    DetectOCRErrors().main()
