from spica_advisor.investigation import InvestigationBuilder
from spica_advisor.investigations.unauthenticated_endpoints.context import UnauthenticatedEndpointsContext
from spica_advisor.investigations.unauthenticated_endpoints.markdown import SECTION
from spica_advisor.investigations.unauthenticated_endpoints.steps import (
    analyze_endpoints,
    find_public_functions,
    prepare_for_analysis,
    read_functions,
    report_unauthenticated_endpoints,
)


def build():
    return (
        InvestigationBuilder("unauthenticated-endpoints")
        .with_context(UnauthenticatedEndpointsContext)
        .with_section(SECTION)
        .step("read functions", read_functions)
        .step("find public functions", find_public_functions)
        .step("prepare for analysis", prepare_for_analysis)
        .step("analyze endpoints", analyze_endpoints)
        .step("report unauthenticated endpoints", report_unauthenticated_endpoints)
        .build()
    )
