import json
from datetime import datetime, timedelta

import logfire
from numpy import broadcast
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.mcp import MCPServerStreamableHTTP

logfire.configure(token="pylf_v1_eu_5K4HWmCfFr2xp8nqkxWvLgJ68W0Rjgcm2RGPtss6FQlc")
logfire.instrument_pydantic_ai()
import json

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIResponsesModel, OpenAIResponsesModelSettings

from app.core.ws import websocket_conn_man
from src.crawler import (
    complex_web_extraction,
    crawl_site,
    get_clean_markdown,
    take_screenshot,
)

model = OpenAIResponsesModel("gpt-5")
# settings = OpenAIResponsesModelSettings(
#     openai_reasoning_effort="low",
#     openai_reasoning_summary="concise",
# )


class BaseDep(BaseModel):
    url: str
    username: str
    password: str
    storage_state_path: str | None = None
    cdp_endpoint: str | None = None
    visited_urls: list[str] = []
    ux_report: list = []
    user_journey: list = []
    positive_stuff: list = []
    expectations: list = []


class CrawlerDep(BaseDep):
    current_page: str


class MainAgentOutput(BaseModel):
    should_continue: bool
    visited_urls: list[str]
    current_purchase_flow_number: int
    total_purchase_flows: int
    decision_points: list[str]
    forced_interactions: list[str]
    abandonment_risks: list[str]
    next_url: str | None = None


server = MCPServerStreamableHTTP("http://localhost:8931/mcp")


class UXRisk(BaseModel):
    issue: str
    user_impact: str


class UXFrictionPoint(BaseModel):
    issue: str
    user_impact: str


class UXReport(BaseModel):
    title: str
    url: str
    risks: list[UXRisk]
    friction_points: list[UXFrictionPoint]


# Main orchestrator agent - coordinates other agents
agent = Agent(
    model="openai:gpt-4o",
    instructions=(
        """You are a UX Analysis Agent with browser control via Playwright MCP. Your mission: systematically audit web pages for usability issues and strengths.

        CORE PRINCIPLES:
        - Stay within the same domain—never navigate to external sites or trigger logout flows
        - Analyze what's visible: UI patterns, content hierarchy, interaction affordances, error states
        - Be specific: cite exact element selectors, text labels, or visual positions when identifying issues

        ANALYSIS WORKFLOW (per page):
        1. Navigate & Wait: Load the target page, wait for key elements to stabilize
        2. Extract Structure: Identify navigation, CTAs, forms, error messages, loading states
        3. Multi-Agent Analysis:
        - UX Critic: friction points (confusing labels, hidden CTAs, poor contrast)
        - User Journey: flow blockers (broken links, unclear next steps, abandonment risks)
        - Expectation Gap: missing features users expect (search, filters, feedback, help)
        - Positive UX: what works well (clear hierarchy, good affordances, accessible patterns)
        - Performance/A11y: load times, ARIA labels, keyboard nav, color contrast
        4. Prioritized Recommendations: actionable fixes ranked by impact (high/medium/low)

        OUTPUT FORMAT:
        Return a structured report per page:
        - Issues categorized by severity (critical/major/minor)
        - Strengths to preserve
        - Top 3-5 recommendations with implementation hints

        SAFETY RULES:
        - Never click logout, delete account, or destructive actions
        - Respect rate limits—add delays between actions if needed"""
    ),
    system_prompt=(
        "You are the Web Analysis Orchestrator. You will do UX analysis of websites by coordinating specialized agents."
    ),
    toolsets=[server],
    deps_type=BaseDep,
    output_type=MainAgentOutput,
)


# UX Analysis Agent - focused on UX insights
ux_agent = Agent(
    "gpt-4o",
    instructions=(
        """You are a UX Critic Agent with Playwright MCP access. Ruthlessly identify usability flaws that harm real users.

        UX RISKS (Blockers):
        - Broken functionality: non-clickable buttons, dead links, unresponsive forms
        - Navigation chaos: hidden menus, unclear labels, orphaned pages
        - Accessibility failures: contrast <4.5:1, missing alt text, no keyboard nav
        - Trust killers: mixed HTTP/HTTPS, unclear branding
        - Performance issues: loads >3s, blocking resources

        UX FRICTION (Pain Points):
        - Unnecessary steps in flows that could be simplified
        - Form problems: excessive required fields, unclear validation
        - CTA confusion: vague labels, poor visual hierarchy
        - Information gaps: hidden pricing, missing help, unclear next steps
        - Visual obstacles: tiny tap targets (<44px), poor contrast, clutter

        RULES:
        - Only report verified issues you observe—no speculation
        - Be specific: cite element selectors or exact text
        - Explain user impact in terms of task failure or frustration
        - Stay within domain—never trigger logout
        - YOU MUST NOT DO ANY ACTION THAT COULD CHANGE CURRENT STATE OF THE PAGE YOU HAVE ONLY READ ACCESS
        """
    ),
    system_prompt="You are a UX Critic that analyzes website data to identify user experience issues.",
    deps_type=BaseDep,
    toolsets=[server],
    output_type=UXReport,
)

crawler_agent = Agent(
    "gpt-4o",
    toolsets=[server],
    instructions=(
        "You are here to get the cleaned Markdown content and links of the page."
        "Use get_web_info tool function to get the cleaned Markdown content and links of the page."
        "If you need more information about the page, use chrome_get_web_content function to get the web content of the page."
        "If you want more descriptive information about the page, you will use get_advanced_web_info function."
    ),
    deps_type=CrawlerDep,
)


@crawler_agent.tool()
async def get_basic_web_info(ctx: RunContext[CrawlerDep], url_to_visit: str):
    """Gets all necessary information like markdown and HTML version of current page to visit and analyze.
    Uses CDP connection to existing Chrome instance where user is already logged in.
    url:str must be the exact url you wanna crawl from
    """
    print("crawling the current page with CDP connection")
    response = await get_clean_markdown(
        ctx.deps.current_page or url_to_visit, cdp_url=ctx.deps.cdp_endpoint or ""
    )
    print("crawling the current page with CDP connection completed")
    print("starting to crawl the current page", response)
    return response


@crawler_agent.tool()
async def get_advanced_web_info(ctx: RunContext[CrawlerDep], url_to_visit: str):
    """Gets all necessary information like markdown and HTML version of current page to visit and analyze.
    It returns the most descriptive information about the page using LLM extraction techniques.
    Uses CDP connection to existing Chrome instance where user is already logged in.
    """
    print("crawling the site to get all the links and button selectors to visit next")
    response = await complex_web_extraction(
        cdp_url=ctx.deps.cdp_endpoint or "",
        url_to_crawl=ctx.deps.current_page or url_to_visit,
    )
    print(
        "crawling the site to get all the links and button selectors to visit next completed"
    )
    print("starting to crawl the site", response)
    return response


# @agent.tool()
# async def get_next_page_to_visit(ctx: RunContext[BaseDep], current_page: str):
#     """Using current page link, this function is goingto return all the links and button selectors to visit next."""
#     print("crawling the site to get all the links and button selectors to visit next")
#     print(current_page)
#     response = await crawler_agent.run(
#         f"Crawl the site and get all the links and button selectors to visit next. ({current_page})",
#         deps=CrawlerDep(
#             url=ctx.deps.url,
#             username=ctx.deps.username,
#             password=ctx.deps.password,
#             storage_state_path=ctx.deps.storage_state_path,
#             cdp_endpoint=ctx.deps.cdp_endpoint,
#             current_page=current_page,
#         ),
#     )
#     print(
#         "crawling the site to get all the links and button selectors to visit next completed"
#     )
#     print("starting to crawl the site", response)
#     return response


@ux_agent.tool()
async def visit_current_page(ctx: RunContext[BaseDep], url: str):
    """url:str must be the exact url you wanna visit and get markdown and html"""
    print("visiting the current page with CDP connection")
    response = await get_clean_markdown(url, cdp_url=ctx.deps.cdp_endpoint or "")
    print("visiting the current page with CDP connection completed")
    print("starting to visit the current page", response)

    return response


@agent.tool()
async def get_user_credentials(ctx: RunContext[BaseDep]):
    """Gets the username and password of the user."""
    return ctx.deps.username, ctx.deps.password


@agent.tool()
async def ux_critic(ctx: RunContext[BaseDep], current_page_url: str):
    """Runs the UX Critic agent on the current page URL."""
    print("Sending data to UX Critic agent for analysis")
    ux_result = await ux_agent.run(
        f"Url to visit is {current_page_url}, Analyze this website data for UX issues and provide actionable improvements",
        deps=ctx.deps,
    )
    ctx.deps.visited_urls.append(current_page_url)
    print("UX Critic agent analysis completed")
    print("UX agent result:", ux_result)
    ctx.deps.ux_report.append(ux_result.output)
    await websocket_conn_man.broadcast(
        json.dumps({"type": "ux_report", "data": ux_result.output.model_dump()})
    )
    return ux_result.output


class UserJourneyAnalysis(BaseModel):
    flow_name: str
    steps_required: int
    decision_points: int
    forced_interactions: list[str]
    abandonment_risks: list[str]


user_journey_agent = Agent(
    "gpt-4o",
    instructions=(
        "You are a User Journey Analyst. Your role is to map end-to-end user flows "
        "such as browsing, registration, checkout, or profile management. "
        "Count steps, highlight decision points, and note forced interactions "
        "that could frustrate users. Identify abandonment risks where users "
        "might quit the process."
        "YOU MUST NOT DO ANY ACTION THAT COULD CHANGE CURRENT STATE OF THE PAGE YOU HAVE ONLY READ ACCESS"
    ),
    system_prompt="You analyze websites by simulating user journeys and documenting them.",
    output_type=list[UserJourneyAnalysis],
    deps_type=BaseDep,
    toolsets=[server],
)


class ExpectationGap(BaseModel):
    area: str
    missing_feature: str
    user_impact: str


expectation_agent = Agent(
    "gpt-4o",
    instructions=(
        "You are an Expectation Gap Analyst. Your role is to detect missing "
        "features or design patterns users normally expect on this type of site "
        "(search bar, filters, reviews, recently viewed items, etc.). "
        "Document what is missing and how it impacts the user."
        "YOU MUST NOT DO ANY ACTION THAT COULD CHANGE CURRENT STATE OF THE PAGE YOU HAVE ONLY READ ACCESS"
    ),
    system_prompt="You detect unmet user expectations and missing standard features.",
    output_type=list[ExpectationGap],
    deps_type=BaseDep,
    toolsets=[server],
)

positive_agent = Agent(
    "gpt-4o",
    instructions=(
        "You are a Positive UX Evaluator. Your role is to highlight strengths "
        "of the website experience (clear CTAs, responsive design, simplicity, speed). "
        "Keep it balanced so the final report is not only negative."
        "YOU MUST NOT DO ANY ACTION THAT COULD CHANGE CURRENT STATE OF THE PAGE YOU HAVE ONLY READ ACCESS"
    ),
    system_prompt="You highlight positive user experience elements.",
    output_type=list[str],
    deps_type=BaseDep,
    toolsets=[server],
)


@agent.tool()
def get_all_visited_urls(ctx: RunContext[BaseDep]):
    """Returns all visited URLs."""
    return ctx.deps.visited_urls


@agent.tool()
async def user_journey_analysis(ctx: RunContext[BaseDep], current_page_url: str):
    """Runs the User Journey Agent on the current page URL."""
    print("Sending data to User Journey Agent for analysis")
    journey_result = await user_journey_agent.run(
        f"Url to visit is {current_page_url}, Analyze this website data for user journeys, flows, and abandonment risks.",
        deps=ctx.deps,
    )
    ctx.deps.visited_urls.append(current_page_url)
    print("User Journey Agent analysis completed")
    print("User Journey agent result:", journey_result)
    ctx.deps.user_journey.extend(journey_result.output)

    await websocket_conn_man.broadcast(
        json.dumps(
            {
                "type": "user_journey",
                "data": [item.model_dump() for item in journey_result.output],
            }
        )
    )
    return journey_result.output


@agent.tool()
async def expectation_gap_analysis(ctx: RunContext[BaseDep], current_page_url: str):
    """Runs the Expectation Gap Agent on the current page URL."""
    print("Sending data to Expectation Gap Agent for analysis")
    expectation_result = await expectation_agent.run(
        f"Url to visit is {current_page_url}, Analyze this website data for missing features and unmet user expectations.",
        deps=ctx.deps,
    )
    ctx.deps.visited_urls.append(current_page_url)
    print("Expectation Gap Agent analysis completed")
    print("Expectation Gap agent result:", expectation_result)
    ctx.deps.expectations.extend(expectation_result.output)
    await websocket_conn_man.broadcast(
        json.dumps(
            {
                "type": "expectation_gap",
                "data": [item.model_dump() for item in expectation_result.output],
            }
        )
    )
    return expectation_result.output


@agent.tool()
async def positive_ux_analysis(ctx: RunContext[BaseDep], current_page_url: str):
    """Runs the Positive UX Agent on the current page URL."""
    print("Sending data to Positive UX Agent for analysis")
    positive_result = await positive_agent.run(
        f"Url to visit is {current_page_url}, Analyze this website data for positive user experience elements and strengths.",
        deps=ctx.deps,
    )
    ctx.deps.visited_urls.append(current_page_url)
    print("Positive UX Agent analysis completed")
    print("Positive UX agent result:", positive_result)
    ctx.deps.positive_stuff.extend(positive_result.output)
    await websocket_conn_man.broadcast(
        json.dumps(
            {
                "type": "positive_ux",
                "data": positive_result.output,
            }
        )
    )
    return positive_result.output


async def main():
    username = "standard_user"
    password = "secret_sauce"
    cdp_endpoint = "http://localhost:9222"

    # start time
    start_time = datetime.now()
    _deps_for_agent = BaseDep(
        url="https://www.saucedemo.com",
        username=username,
        password=password,
        cdp_endpoint=cdp_endpoint,
        visited_urls=[],
        ux_report=[],
        user_journey=[],
        positive_stuff=[],
        expectations=[],
    )
    result = await agent.run(
        """Go https://www.saucedemo.com and start the analysis of the website. FYI: This is an e-commerce site for purchasing branded merchandise.""",
        deps=_deps_for_agent,
    )
    _deps_for_agent.visited_urls.extend(result.output.visited_urls)

    while True:
        if result.output.should_continue:
            print("Continuing to next page...")
            result = await agent.run(
                f"""Go to {result.output.next_url} and continue the analysis. 
                Current progress: {result.output.current_purchase_flow_number}/{result.output.total_purchase_flows} purchase flows completed. 
                Visited URLs so far: {', '.join(_deps_for_agent.visited_urls)}.""",
                deps=BaseDep(
                    url=result.output.next_url or "https://www.saucedemo.com",
                    username=username,
                    password=password,
                    cdp_endpoint=cdp_endpoint,
                ),
                message_history=result.all_messages(),
            )
            _deps_for_agent.visited_urls.extend(result.output.visited_urls)

        else:
            print("Analysis complete.")
            break
        # timeout after 2 minutes
        if datetime.now() - start_time > timedelta(minutes=2):
            print("Timeout reached, stopping analysis.")
            break
    print(result.output)
    await websocket_conn_man.broadcast(
        json.dumps({"type": "final_report", "data": result.output.model_dump()})
    )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
