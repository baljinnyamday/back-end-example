from datetime import datetime, timedelta

from fastapi import APIRouter

from app.api.routes.analysis.schema import AnalysisRequest
from src.main import BaseDep, agent

router = APIRouter(prefix="/analysis", tags=["Analysis Endpoint"])


@router.post("/")
async def analyse_website_ux(inputs: AnalysisRequest):
    try:
        username = "standard_user"
        password = "secret_sauce"
        cdp_endpoint = "http://localhost:9222"

        # start time
        start_time = datetime.now()
        _deps_for_agent = BaseDep(
            url=inputs.url_to_analyse or "https://www.saucedemo.com",
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
            f"""Go to {inputs.url_to_analyse} and start the analysis of the website. FYI: {inputs.prompt}""",
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
                        url=result.output.next_url
                        or inputs.url_to_analyse
                        or "https://www.saucedemo.com",
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
        print(result)
        print("Final UX Report:")
        print("Visited URLs:", set(_deps_for_agent.visited_urls))
        print("UX Reports:", _deps_for_agent.ux_report)
        print("User Journeys:", _deps_for_agent.user_journey)
        print("Expectation Gaps:", _deps_for_agent.expectations)
        print("Positive UX Elements:", _deps_for_agent.positive_stuff)
        return {
            "visited_urls": set(_deps_for_agent.visited_urls),
            "ux_report": _deps_for_agent.ux_report,
            "user_journey": _deps_for_agent.user_journey,
            "expectations": _deps_for_agent.expectations,
            "positive_stuff": _deps_for_agent.positive_stuff,
            "final_result": result,
        }
    except Exception as e:
        return {"error": str(e)}
