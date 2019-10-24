import ast
import logging
import sys

from .dumb_scope_visitor import DumbScopeVisitor
from .constants import HTTP_VERBS

logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(stream=sys.stderr)
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

class UseTimeout(object):
    name = "UseTimeout"
    version = "0.0.1"
    code = "R2C702"

    def __init__(self, tree):
        self.tree = tree

    def run(self):
        visitor = UseTimeoutVisitor()
        visitor.visit(self.tree)

        for report in visitor.report_nodes:
            node = report['node']
            yield (
                node.lineno,
                node.col_offset,
                self._message_for(),
                self.name,
            )

    def _message_for(self):
        return f"{self.code} use a timeout; requests will hang forever without a timeout (recommended 60 sec)"

class UseTimeoutVisitor(DumbScopeVisitor):

    def visit_Call(self, call_node):
        logger.debug(f"Visiting Call node: {ast.dump(call_node)}")
        if not call_node.func:
            logger.debug("Call node func does not exist")
            return

        if not isinstance(call_node.func, ast.Attribute):
            logger.debug("Call node func is not an ast.Attribute")
            return

        attribute = call_node.func

        if not attribute.value.id == "requests" and not attribute.attr in HTTP_VERBS:
            logger.debug("Call node is not a requests API call")
            return

        if not call_node.keywords:
            logger.debug("No keywords on Call node")
            return

        keywords = call_node.keywords
        if any([kw.arg == "timeout" for kw in keywords]):
            logger.debug("requests call has the 'timeout' keyword, so we're good")
            return

        logger.debug(f"Found this node: {ast.dump(call_node)}")
        self.report_nodes.append({
            "node": call_node,
        })

if __name__ == "__main__":
    import argparse

    logger.setLevel(logging.DEBUG)

    parser = argparse.ArgumentParser()
    # Add arguments here
    parser.add_argument("inputfile")

    args = parser.parse_args()

    logger.info(f"Parsing {args.inputfile}")
    with open(args.inputfile, 'r') as fin:
        tree = ast.parse(fin.read())

    visitor = UseTimeoutVisitor()
    visitor.visit(tree)