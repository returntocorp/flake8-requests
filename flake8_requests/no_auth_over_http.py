import ast
import logging
import sys

from flake8_requests.requests_base_visitor import RequestsBaseVisitor
from flake8_requests import __version__

logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(stream=sys.stderr)
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

class NoAuthOverHttp(object):
    name = "r2c-requests-no-auth-over-http"
    version = __version__

    def __init__(self, tree):
        self.tree = tree

    def run(self):
        visitor = NoAuthOverHttpVisitor()
        visitor.visit(self.tree)

        for report in visitor.report_nodes:
            node = report['node']
            urls = report['urls']
            yield (
                node.lineno,
                node.col_offset,
                self._message_for(urls),
                self.name,
            )

    def _message_for(self, urls):
        return f"{self.name} auth is possibly used over http://, which could expose credentials. possible_urls: {urls}"

class NoAuthOverHttpVisitor(RequestsBaseVisitor):

    def __init__(self):
        super(NoAuthOverHttpVisitor, self).__init__()

    def _is_http(self, parsed_url):
        if parsed_url and parsed_url.scheme == "http":
            return True
        return False

    def _see_if_possible_urls_fails_this_check(self, urls):
        return any( [self._is_http(url) for url in urls] )

    def visit_Call(self, call_node):
        logger.debug(f"Visiting Call node: {ast.dump(call_node)}")
        if not call_node.func:
            logger.debug("Call node func does not exist")
            return

        fxn_name = self._get_function_name(call_node)
        if not self.is_method(call_node, fxn_name):
            logger.debug(f"Call node is not a requests API call: {fxn_name}")
            return

        if not call_node.keywords:
            logger.debug("No keywords on Call node, don't care")
            return

        keywords = call_node.keywords
        if not any([kw.arg == "auth" for kw in keywords]):
            logger.debug("requests call does not contain the 'auth' keyword")
            return

        if not call_node.args:
            logger.debug("No args on Call node")
            return


        url_arg = self._get_url_arg(call_node, fxn_name)
        possible_urls = self._get_possible_urls_from_arg(url_arg)
        if not self._see_if_possible_urls_fails_this_check(possible_urls):
            logger.debug("url is not http, so it's fine")
            return

        logger.debug(f"Found this node: {ast.dump(call_node)}")
        self.report_nodes.append({
            "node": call_node,
            "urls": [url.geturl() for url in possible_urls]
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

    visitor = NoAuthOverHttpVisitor()
    visitor.visit(tree)