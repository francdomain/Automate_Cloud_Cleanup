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

      if (action.value === "approve") {
        await axios.post(
          `https://api.github.com/repos/${process.env.REPO_OWNER}/${process.env.REPO_NAME}/dispatches`,
          {
            event_type: "approve_cleanup",
          },
          {
            headers: {
              Authorization: `Bearer ${process.env.GITHUB_TOKEN}`,
              "Content-Type": "application/json",
            }
          }
        );

        return {
          statusCode: 200,
          body: JSON.stringify({ text: "The cleanup workflow has been approved." }),
        };
      } else if (action.value === "decline") {
        return {
          statusCode: 200,
          body: JSON.stringify({ text: "The cleanup workflow has been declined." }),
        };
      }
    }

    return {
      statusCode: 200,
      body: "No action taken.",
    };
  } catch (error) {
    console.error("Error:", error);
    return {
      statusCode: 500,
      body: JSON.stringify({ error: "Internal server error." }),
    };
  }
};