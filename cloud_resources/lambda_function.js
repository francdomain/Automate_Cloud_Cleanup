const axios = require("axios");

exports.handler = async (event) => {
  try {
    const body = JSON.parse(event.body);

    if (body.type === "url_verification") {
      return {
        statusCode: 200,
        body: body.challenge,
      };
    }

    if (body.type === "interactive_message") {
      const action = body.actions[0];

      const approvalStatus = action.value === "approve" ? "approved" : "declined";

      try {
        await axios.post(
          `https://api.github.com/repos/${process.env.REPO_OWNER}/${process.env.REPO_NAME}/dispatches`,
          {
            event_type: "slack-approval",
            client_payload: {
              approval_status: approvalStatus,
            },
          },
          {
            headers: {
              Authorization: `Bearer ${process.env.GITHUB_TOKEN}`,
              "Content-Type": "application/json",
            },
          }
        );
        return {
          statusCode: 200,
          body: JSON.stringify({
            text: `The cleanup workflow has been ${approvalStatus}.`,
          }),
        };
      } catch (error) {
        console.error("GitHub API Error:", error.response?.data || error.message);
        return {
          statusCode: 500,
          body: JSON.stringify({
            text: `An error occurred while triggering the workflow: ${error.message}`,
          }),
        };
      }
    }

    return {
      statusCode: 200,
      body: "No action taken.",
    };
  } catch (error) {
    console.error("Error:", error.message);
    return {
      statusCode: 500,
      body: JSON.stringify({ error: "Internal server error." }),
    };
  }
};