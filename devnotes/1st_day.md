currently 

ive done last night:
1. story agent, takes manager agent and context to produce story_scene, and options(list)
2. image agent, takes story agent and manager agent output and context to produce image prompt, image moodel choices, image file

to test you can run test_manager, test_story_agent, test_image_agent, test_video_agent



whats need to be done
Urgent:
1. video agent, requirement listed in the video_agent.md in my devnotes folder (Peter branch)
2. data flow matching, data flow for each agent, In and Output schema, need to ensure its matching the flow and can be parsed by downstream


When we have time:
3. frontend connection, Quansheng is developing frontend we need to provide the output type and format for him to construct the frontend connection
4. database structure set up and connection to save and retrive instead of relying on the context in terminal
5. construct a thorough test suite for each agent, and test the data flow

For Shaun:
Could you please help us draft a thorough documentation 
for  the flow chart and each agent role and function, you can use 
OpenAI O-1 or perplexity R1 to help you write the documentation.


