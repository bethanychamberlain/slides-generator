"""Canvas QTI export for quiz import."""

import uuid
import zipfile
from io import BytesIO
from xml.sax.saxutils import escape


def _make_id():
    return f"g{uuid.uuid4().hex[:16]}"


def _esc(text):
    """Escape text for safe XML interpolation."""
    return escape(str(text))


def create_canvas_qti(questions_by_slide, quiz_title="Note-Taking Quiz"):
    """Generate a Canvas-compatible QTI ZIP file for quiz import."""

    assessment_id = _make_id()

    qti_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<questestinterop xmlns="http://www.imsglobal.org/xsd/ims_qtiasiv1p2"
                 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                 xsi:schemaLocation="http://www.imsglobal.org/xsd/ims_qtiasiv1p2 http://www.imsglobal.org/xsd/ims_qtiasiv1p2p1.xsd">
  <assessment ident="{assessment_id}" title="{_esc(quiz_title)}">
    <qtimetadata>
      <qtimetadatafield>
        <fieldlabel>qmd_timelimit</fieldlabel>
        <fieldentry></fieldentry>
      </qtimetadatafield>
    </qtimetadata>
    <section ident="root_section">
'''

    question_num = 0
    for slide_num, questions in questions_by_slide.items():
        for q in questions:
            question_num += 1
            qtype = q.get("type", "open_ended")
            q_id = _make_id()

            if qtype == "multiple_choice":
                question_text = _esc(q.get("question", ""))
                options = q.get("options", [])
                correct = q.get("answer", "")

                responses_xml = ""
                correct_id = ""
                for opt in options:
                    opt_id = _make_id()
                    if opt.startswith(correct):
                        correct_id = opt_id
                    responses_xml += f'''
              <response_label ident="{opt_id}">
                <material><mattext texttype="text/html">{_esc(opt)}</mattext></material>
              </response_label>'''

                qti_xml += f'''
      <item ident="{q_id}" title="Question {question_num}">
        <itemmetadata>
          <qtimetadata>
            <qtimetadatafield>
              <fieldlabel>question_type</fieldlabel>
              <fieldentry>multiple_choice_question</fieldentry>
            </qtimetadatafield>
          </qtimetadata>
        </itemmetadata>
        <presentation>
          <material><mattext texttype="text/html">{question_text}</mattext></material>
          <response_lid ident="response1" rcardinality="Single">
            <render_choice>{responses_xml}
            </render_choice>
          </response_lid>
        </presentation>
        <resprocessing>
          <outcomes><decvar maxvalue="100" minvalue="0" varname="SCORE" vartype="Decimal"/></outcomes>
          <respcondition continue="No">
            <conditionvar><varequal respident="response1">{correct_id}</varequal></conditionvar>
            <setvar action="Set" varname="SCORE">100</setvar>
          </respcondition>
        </resprocessing>
      </item>
'''

            elif qtype == "true_false":
                statement = _esc(q.get("statement", ""))
                answer = q.get("answer", True)
                true_id = _make_id()
                false_id = _make_id()
                correct_id = true_id if answer else false_id

                qti_xml += f'''
      <item ident="{q_id}" title="Question {question_num}">
        <itemmetadata>
          <qtimetadata>
            <qtimetadatafield>
              <fieldlabel>question_type</fieldlabel>
              <fieldentry>true_false_question</fieldentry>
            </qtimetadatafield>
          </qtimetadata>
        </itemmetadata>
        <presentation>
          <material><mattext texttype="text/html">{statement}</mattext></material>
          <response_lid ident="response1" rcardinality="Single">
            <render_choice>
              <response_label ident="{true_id}">
                <material><mattext texttype="text/html">True</mattext></material>
              </response_label>
              <response_label ident="{false_id}">
                <material><mattext texttype="text/html">False</mattext></material>
              </response_label>
            </render_choice>
          </response_lid>
        </presentation>
        <resprocessing>
          <outcomes><decvar maxvalue="100" minvalue="0" varname="SCORE" vartype="Decimal"/></outcomes>
          <respcondition continue="No">
            <conditionvar><varequal respident="response1">{correct_id}</varequal></conditionvar>
            <setvar action="Set" varname="SCORE">100</setvar>
          </respcondition>
        </resprocessing>
      </item>
'''

            elif qtype == "short_answer":
                prompt_text = _esc(q.get("prompt", ""))
                answer = _esc(q.get("answer", ""))

                qti_xml += f'''
      <item ident="{q_id}" title="Question {question_num}">
        <itemmetadata>
          <qtimetadata>
            <qtimetadatafield>
              <fieldlabel>question_type</fieldlabel>
              <fieldentry>short_answer_question</fieldentry>
            </qtimetadatafield>
          </qtimetadata>
        </itemmetadata>
        <presentation>
          <material><mattext texttype="text/html">{prompt_text}</mattext></material>
          <response_str ident="response1" rcardinality="Single">
            <render_fib><response_label ident="answer1"/></render_fib>
          </response_str>
        </presentation>
        <resprocessing>
          <outcomes><decvar maxvalue="100" minvalue="0" varname="SCORE" vartype="Decimal"/></outcomes>
          <respcondition continue="No">
            <conditionvar><varequal respident="response1">{answer}</varequal></conditionvar>
            <setvar action="Set" varname="SCORE">100</setvar>
          </respcondition>
        </resprocessing>
      </item>
'''

            elif qtype == "fill_in_blank":
                sentence = _esc(q.get("sentence", "").replace("_____", "[blank]"))
                answer = _esc(q.get("answer", ""))

                qti_xml += f'''
      <item ident="{q_id}" title="Question {question_num}">
        <itemmetadata>
          <qtimetadata>
            <qtimetadatafield>
              <fieldlabel>question_type</fieldlabel>
              <fieldentry>short_answer_question</fieldentry>
            </qtimetadatafield>
          </qtimetadata>
        </itemmetadata>
        <presentation>
          <material><mattext texttype="text/html">{sentence}</mattext></material>
          <response_str ident="response1" rcardinality="Single">
            <render_fib><response_label ident="answer1"/></render_fib>
          </response_str>
        </presentation>
        <resprocessing>
          <outcomes><decvar maxvalue="100" minvalue="0" varname="SCORE" vartype="Decimal"/></outcomes>
          <respcondition continue="No">
            <conditionvar><varequal respident="response1">{answer}</varequal></conditionvar>
            <setvar action="Set" varname="SCORE">100</setvar>
          </respcondition>
        </resprocessing>
      </item>
'''

            elif qtype == "open_ended":
                question_text = _esc(q.get("question", ""))

                qti_xml += f'''
      <item ident="{q_id}" title="Question {question_num}">
        <itemmetadata>
          <qtimetadata>
            <qtimetadatafield>
              <fieldlabel>question_type</fieldlabel>
              <fieldentry>essay_question</fieldentry>
            </qtimetadatafield>
          </qtimetadata>
        </itemmetadata>
        <presentation>
          <material><mattext texttype="text/html">{question_text}</mattext></material>
          <response_str ident="response1" rcardinality="Single">
            <render_fib><response_label ident="answer1" rshuffle="No"/></render_fib>
          </response_str>
        </presentation>
        <resprocessing>
          <outcomes><decvar maxvalue="100" minvalue="0" varname="SCORE" vartype="Decimal"/></outcomes>
        </resprocessing>
      </item>
'''

            elif qtype == "put_in_order":
                instruction = _esc(q.get("instruction", "Arrange in order:"))
                items = q.get("items", [])
                items_text = _esc(", ".join(items))
                qti_xml += f'''
      <item ident="{q_id}" title="Question {question_num}">
        <itemmetadata>
          <qtimetadata>
            <qtimetadatafield>
              <fieldlabel>question_type</fieldlabel>
              <fieldentry>essay_question</fieldentry>
            </qtimetadatafield>
          </qtimetadata>
        </itemmetadata>
        <presentation>
          <material><mattext texttype="text/html">{instruction} {items_text}</mattext></material>
          <response_str ident="response1" rcardinality="Single">
            <render_fib><response_label ident="answer1" rshuffle="No"/></render_fib>
          </response_str>
        </presentation>
        <resprocessing>
          <outcomes><decvar maxvalue="100" minvalue="0" varname="SCORE" vartype="Decimal"/></outcomes>
        </resprocessing>
      </item>
'''

    qti_xml += '''
    </section>
  </assessment>
</questestinterop>'''

    # Create manifest XML
    resource_id = _make_id()
    manifest_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<manifest identifier="{_make_id()}" xmlns="http://www.imsglobal.org/xsd/imsccv1p1/imscp_v1p1">
  <metadata>
    <schema>IMS Content</schema>
    <schemaversion>1.1.3</schemaversion>
  </metadata>
  <organizations/>
  <resources>
    <resource identifier="{resource_id}" type="imsqti_xmlv1p2" href="{assessment_id}.xml">
      <file href="{assessment_id}.xml"/>
    </resource>
  </resources>
</manifest>'''

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('imsmanifest.xml', manifest_xml)
        zf.writestr(f'{assessment_id}.xml', qti_xml)

    buffer.seek(0)
    return buffer
