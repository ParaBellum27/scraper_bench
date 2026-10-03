scraping benchmarking project
unstructured v structured data types
types of tools it has access to
can it break off walls

models tested on: Luna, Mistral Medium 3.5, Gemini 3.8 Flash

I want to move away from doing 10-K reports, as in order to make it a good benchmark I would have to read through all of, say, 100 or 10 10-Ks. Each is 100 to 300 pages and that's not something I can feasibly do as a human. I don't have the money to contract people to do it for me.

I have a possible other solution that I need you to inspect and show me the feasibility of, and whether it would still serve as a better alternative or a good solution for what I want to build. 
I have a private ed quilty class and a bunch of my classmates have done it. One of the homework assignments in it they ask students to build an LBO model that is then graded by the professor, given a certain score: an A-, 90/100, 80/100, graded by a TA. Those students need to take a company that's already publicly online and then they get the information that they want and then they build an LBO model to take that company private. I have a bunch of classmates who are open to giving me their homework answers: how they did, what they submitted, the grade they got, all of that. I would, in turn, sandbox the whole thing and run my own benchmark based on that information. Force the model to write code. The files should not be accessible to it and should only be accessible through programmatic access. We give it some temporary code scaffold that has access to a file that the model itself cannot access without the code. That same boxing is a bit difficult to figure out. We figure that out. We force the model to write code to access the file and from there the model has to generate the insights. It has to use code to do it but also has an extra level of thinking and reasoning that it otherwise has. 

The model runs in one sandbox. There are no files or data that are accessible to this model inside this sandbox except for one tool and one Python file. The model is forced to write all its code in one Python file and then submit this Python file to another workspace. This workspace executes the Python code and sends a response back to the model. 

